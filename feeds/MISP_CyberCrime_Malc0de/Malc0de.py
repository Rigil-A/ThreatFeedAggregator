# IP Blacklist
import requests, csv, ipaddress, time
from datetime import datetime
from urllib.parse import urlparse

SOURCES = [
    "https://iplists.firehol.org/files/malc0de.ipset",           
    "https://malc0de.com/bl/IP_Blacklist.txt",                   
    "https://malc0de.com/bl/ZONES",                             
    "https://malc0de.com/bl/BOOT",                              
    "https://malc0de.com/database/"                               
]

OUT_CSV = "aggregated_malc0de.csv"
TIMEOUT = 20

def fetch_text(url):
    try:
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code == 200 and r.text:
            return r.text
        else:
            print(f"[WARN] {url} returned status {r.status_code}")
    except Exception as e:
        print(f"[ERR] fetch {url}: {e}")
    return None

def lines_from_ipset(text):
    return [l.strip() for l in text.splitlines() if l.strip() and not l.lstrip().startswith('#')]

def extract_hosts_from_html(html):
    import re
    candidates = set(re.findall(r'([a-z0-9.-]+\.[a-z]{2,}|(?:\d{1,3}\.){3}\d{1,3})', html, flags=re.I))
    return [c for c in candidates]

def detect_type(value):
    try:
        ipaddress.ip_address(value)
        return "ip"
    except Exception:
        return "domain"

def normalize(value):
    return value.strip().lower()

def main():
    seen = {}  
    for src in SOURCES:
        print("Fetching", src)
        text = fetch_text(src)
        if not text:
            continue

        parsed = urlparse(src)
        if src.endswith(".ipset") or "IP_Blacklist" in src:
            items = lines_from_ipset(text)
        elif src.endswith("/database/") or '<html' in text.lower():
            items = extract_hosts_from_html(text)
        else:
            # default: lines split and ignore comments
            items = lines_from_ipset(text)

        for it in items:
            v = normalize(it)
            t = detect_type(v)
            if v not in seen:
                seen[v] = {"type": t, "sources": set(), "first_seen": datetime.utcnow().isoformat() + "Z"}
            seen[v]["sources"].add(src)

        # small politeness delay
        time.sleep(1)

    # write CSV
    now = datetime.utcnow().isoformat() + "Z"
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["value","type","sources","first_seen","fetched_at"])
        writer.writeheader()
        for v, meta in sorted(seen.items()):
            writer.writerow({
                "value": v,
                "type": meta["type"],
                "sources": ";".join(sorted(meta["sources"])),
                "first_seen": meta["first_seen"],
                "fetched_at": now
            })

    print(f"Wrote {len(seen)} indicators to {OUT_CSV}")

if __name__ == "__main__":
    main()
