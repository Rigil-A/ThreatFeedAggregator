# This feed focuses on crimeware command-and-control infrastructure and helps track and disrupt malware campaigns.
import requests
import csv
from io import StringIO
import ipaddress
from datetime import datetime, timezone

CSV_URL = "https://cybercrime-tracker.net/csv.php"  
OUT_CSV = "cybercrime_tracker.csv"
TIMEOUT = 30


POSSIBLE_VALUE_COLS = [
    "ip", "ip_address", "ipaddr", "address", "host", "domain", "hostname", "url", "source"
]

def detect_type(value: str) -> str:
    try:
        ipaddress.ip_address(value)
        return "ip"
    except Exception:
        v = value.strip().lower()
        if "/" in v:
            return "network"
        if "." in v and any(c.isalpha() for c in v):
            return "domain"
        return "unknown"

def normalize_value(v: str) -> str:
    return v.strip()

def try_parse_as_csv(text: str):
    """
    Trả về (reader_rows, header_fieldnames or None).
    reader_rows là list[dict] nếu header exists, ngược lại list[list]
    """
    sample = text[:4096]
    sniffer = csv.Sniffer()
    has_header = False
    dialect = csv.get_dialect('excel')
    try:
        dialect = sniffer.sniff(sample)
        has_header = sniffer.has_header(sample)
    except Exception:
        dialect = csv.get_dialect('excel')
        has_header = False

    f = StringIO(text)
    if has_header:
        reader = csv.DictReader(f, dialect=dialect)
        rows = list(reader)
        return rows, reader.fieldnames
    else:
        f.seek(0)
        reader = csv.reader(f, dialect=dialect)
        rows = [r for r in reader if r and any(cell.strip() for cell in r)]
        return rows, None

def find_value_in_dict(row_dict, fieldnames):
    for col in POSSIBLE_VALUE_COLS:
        if col in row_dict and row_dict[col].strip():
            return row_dict[col].strip()
    for k, v in row_dict.items():
        if v and any(ch.isalnum() for ch in v):
            s = v.strip()
            if "." in s or ":" in s:
                return s
    return None

def main():
    try:
        r = requests.get(CSV_URL, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print("Error fetching URL:", e)
        return

    text = r.text
    fetched_at = datetime.now(timezone.utc).isoformat()
    parsed, header = try_parse_as_csv(text)

    results = []
    if header:  # parsed is list of dicts
        for row in parsed:
            value = find_value_in_dict(row, header)
            if not value:
                # skip rows without recognizable field
                continue
            v = normalize_value(value)
            t = detect_type(v)
            results.append({
                "value": v,
                "type": t,
                "source": CSV_URL,
                "fetched_at": fetched_at,
                "raw_row": "|".join((str(row.get(h,"")).replace("\n"," ") for h in header))
            })
    else:
        # parsed is list of lists; try to guess which column holds ip/domain
        for row in parsed:
            # find first cell that looks like ip/domain
            chosen = None
            for cell in row:
                if not cell:
                    continue
                s = cell.strip()
                # heuristic: has digit and dot (ipv4) or has a letter+dot (domain)
                if any(ch.isdigit() for ch in s) and "." in s or ("." in s and any(c.isalpha() for c in s)):
                    chosen = s
                    break
            if not chosen:
                # fallback: take first non-empty cell
                chosen = row[0].strip()
            v = normalize_value(chosen)
            t = detect_type(v)
            results.append({
                "value": v,
                "type": t,
                "source": CSV_URL,
                "fetched_at": fetched_at,
                "raw_row": "|".join(cell.replace("\n"," ") for cell in row)
            })

    if not results:
        print("No indicators parsed from feed.")
        return

    # write to CSV, dedupe by value
    seen = set()
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as outf:
        fieldnames = ["value", "type", "source", "fetched_at", "raw_row"]
        writer = csv.DictWriter(outf, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            if r["value"] in seen:
                continue
            seen.add(r["value"])
            writer.writerow(r)

    print(f"Wrote {len(seen)} unique indicators to {OUT_CSV}")

if __name__ == "__main__":
    main()
