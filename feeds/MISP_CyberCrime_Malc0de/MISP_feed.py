#!/usr/bin/env python3
"""
Fetch public feeds listed on https://www.misp-project.org/feeds/
Saves files into ./feeds/ preserving filename.
Usage:
    python fetch_misp_feeds.py
    python fetch_misp_feeds.py --only-ext .ipset,.txt
    python fetch_misp_feeds.py --outdir /tmp/mispfeeds
"""
import os
import sys
import time
import argparse
import logging
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# Defaults
FEEDS_PAGE = "https://www.misp-project.org/feeds/"
OUTDIR_DEFAULT = "feeds"
USER_AGENT = "misp-feed-fetcher/1.0 (+https://github.com/your-repo)"

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def fetch_url_text(session, url, timeout=20, allow_insecure=False):
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text, resp
    except requests.exceptions.SSLError as e:
        logging.warning("SSL error fetching %s: %s", url, e)
        if allow_insecure:
            logging.warning("Retrying with verify=False for %s (insecure).", url)
            resp = session.get(url, timeout=timeout, verify=False)
            resp.raise_for_status()
            return resp.text, resp
        raise


def find_feed_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # skip anchors and mailto
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        full = urljoin(base_url, href)
        # Heuristics: accept if path ends with common feed ext or contains 'download' or 'files'
        parsed = urlparse(full)
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in (".csv", ".txt", ".json", ".ipset", ".zip", ".gz", ".bz2")) \
           or "download" in path or "files" in path or "feeds" in path:
            links.append((full, a.get_text(strip=True)))
        else:
            # also include links that look like feed pages (may point to raw)
            if "malc0de" in full or "firehol" in full or "abuse" in full or "cybercrime" in full:
                links.append((full, a.get_text(strip=True)))
    # dedupe preserve order
    seen = set()
    out = []
    for l, t in links:
        if l not in seen:
            seen.add(l)
            out.append((l, t))
    return out


def safe_filename_from_url(url):
    p = urlparse(url).path
    name = os.path.basename(p) or p.strip("/").replace("/", "_")
    # fallback
    if not name:
        name = url.replace("://", "_").replace("/", "_")
    return name


def download_feed(session, url, outdir, allow_insecure=False, max_retries=3):
    fname = safe_filename_from_url(url)
    # if url has query giving a filename, use it
    if urlparse(url).query:
        # try to use last path segment + query
        fname = fname + "_" + urlparse(url).query.replace("=", "_").replace("&", "_")
    outpath = os.path.join(outdir, fname)
    # try to GET with streaming
    for attempt in range(1, max_retries + 1):
        try:
            logging.info("[%d/%d] Downloading %s -> %s", attempt, max_retries, url, outpath)
            r = session.get(url, stream=True, timeout=30, allow_redirects=True)
            r.raise_for_status()
            # Try to determine filename from headers if provided
            cd = r.headers.get("content-disposition")
            if cd and "filename=" in cd:
                import re
                m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^;"\']+)', cd)
                if m:
                    fname2 = m.group(1)
                    outpath = os.path.join(outdir, fname2)
            # Save
            total = int(r.headers.get("content-length") or 0)
            with open(outpath, "wb") as fh:
                if total:
                    with tqdm(total=total, unit="B", unit_scale=True, desc=fname, leave=False) as pbar:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                fh.write(chunk)
                                pbar.update(len(chunk))
                else:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
            # write metadata
            meta_path = outpath + ".meta"
            with open(meta_path, "w", encoding="utf-8") as mf:
                mf.write(f"source: {url}\n")
                mf.write(f"fetched_at: {datetime.now(timezone.utc).isoformat()}\n")
                mf.write(f"content-type: {r.headers.get('content-type')}\n")
                mf.write(f"status_code: {r.status_code}\n")
            return outpath
        except requests.exceptions.SSLError as e:
            logging.warning("SSL error fetching %s: %s", url, e)
            if allow_insecure:
                logging.warning("Retrying insecurely (verify=False) for %s", url)
                try:
                    r = session.get(url, stream=True, timeout=30, verify=False)
                    r.raise_for_status()
                    with open(outpath, "wb") as fh:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                fh.write(chunk)
                    return outpath
                except Exception as e2:
                    logging.error("Insecure retry failed for %s: %s", url, e2)
            else:
                logging.error("SSL error and insecure not allowed. Skipping %s", url)
                return None
        except Exception as e:
            logging.warning("Attempt %d failed for %s: %s", attempt, url, e)
            time.sleep(1 + attempt)
    logging.error("All attempts failed for %s", url)
    return None


def main(argv):
    parser = argparse.ArgumentParser(description="Fetch public MISP feeds listed on misp-project.org")
    parser.add_argument("--page", default=FEEDS_PAGE, help="Feeds list page (default misp feeds page)")
    parser.add_argument("--outdir", default=OUTDIR_DEFAULT, help="Output directory")
    parser.add_argument("--only-ext", default=None, help="Comma-separated extensions to keep (e.g. .ipset,.csv)")
    parser.add_argument("--allow-insecure", action="store_true", help="Allow insecure TLS fallback for bad certs (not recommended)")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between downloads")
    args = parser.parse_args(argv)

    os.makedirs(args.outdir, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})

    # fetch feeds page
    try:
        html, resp = fetch_url_text(session, args.page, allow_insecure=args.allow_insecure)
    except Exception as e:
        logging.error("Failed to fetch feeds page %s: %s", args.page, e)
        sys.exit(2)

    feed_links = find_feed_links(html, args.page)
    logging.info("Found %d candidate links on feeds page", len(feed_links))
    # filter by extension if requested
    if args.only_ext:
        wanted = [e.strip().lower() for e in args.only_ext.split(",") if e.strip()]
        feed_links = [fl for fl in feed_links if any(fl[0].lower().endswith(ext) for ext in wanted)]
        logging.info("After ext filter, %d links remain", len(feed_links))

    # Download each
    downloaded = []
    for url, text in feed_links:
        outpath = download_feed(session, url, args.outdir, allow_insecure=args.allow_insecure)
        if outpath:
            downloaded.append(outpath)
        time.sleep(args.sleep)

    logging.info("Done. Downloaded %d files to %s", len(downloaded), args.outdir)
    for p in downloaded:
        logging.info(" - %s", p)


if __name__ == "__main__":
    main(sys.argv[1:])
