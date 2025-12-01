# fetchers/downloader.py
import requests
import time
import random
from requests.exceptions import RequestException, Timeout, SSLError, ConnectionError
import logging 

# -----------------------------
# Global session pool (tối ưu)
# -----------------------------
session = requests.Session()
session.headers.update({
    "User-Agent": "ThreatFeedAggregator/1.0 (+https://example.com)",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
})

# -----------------------------
# Downloader hoàn chỉnh
# -----------------------------

def fetch_feed(
    feed,
    retries=4,
    base_backoff=1.5,
    timeout=(10, 30)  # connect_timeout=10s, read_timeout=30s
):


    url = feed.url if hasattr(feed, "url") else feed  # fallback nếu feed chỉ là string

    for attempt in range(1, retries + 1):
        try:
            # Request
            resp = session.get(url, timeout=timeout)

            # Nếu server trả HTTP error -> raise (ví dụ 500, 404)
            resp.raise_for_status()

            # Decode safe
            try:
                text = resp.text
            except UnicodeDecodeError:
                text = resp.content.decode("utf-8", errors="ignore")

            return text

        except (Timeout, ConnectionError) as e:
            print(f"[TIMEOUT] {url} | Attempt {attempt}/{retries}: {e}")

        except SSLError as e:
            print(f"[SSL ERROR] {url} | Attempt {attempt}/{retries}: {e}")

        except RequestException as e:
            # Bao gồm HTTPError, ConnectionError, TooManyRedirects, v.v.
            print(f"[REQUEST ERROR] {url} | Attempt {attempt}/{retries}: {e}")

        # Retry nếu attempt < retries
        if attempt < retries:
            # Exponential backoff + jitter tránh bị block
            sleep_time = (base_backoff ** attempt) + random.uniform(0.5, 1.5)
            print(f"[RETRY] Sleeping {sleep_time:.1f}s before retry...")
            time.sleep(sleep_time)

    print(f"[FAILED] Giving up on {url}")
    return ""  # về dạng empty string để parser skip
