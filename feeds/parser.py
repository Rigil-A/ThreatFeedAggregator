# fetchers/parsers.py

import csv
import json
import re
from io import StringIO
import ipaddress

# ========================================================
# 1. IOC Regex mạnh (IP + Domain + URL + Email + Hash)
# ========================================================

IP_REGEX = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
DOMAIN_REGEX = r"\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b"
URL_REGEX = r"https?://[^\s'\"]+"
EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
HASH_REGEX = r"\b[a-fA-F0-9]{32,64}\b"  # MD5/SHA1/SHA256

IOC_REGEXES = [
    IP_REGEX,
    DOMAIN_REGEX,
    URL_REGEX,
    EMAIL_REGEX,
    HASH_REGEX,
]

# ========================================================
# 2. Helper: Kiểm tra IP private/local
# ========================================================

import ipaddress
def is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except:
        return False

# ========================================================
# 3. Clean IOC
# ========================================================

def clean_ioc(value: str) -> str:
    value = value.strip().strip(",").strip(";").strip("[](){}")
    value = value.replace("\\", "")
    return value.lower()

# ========================================================
# 4. Detect IOC type
# ========================================================

def detect_ioc_type(value: str) -> str:
    if re.fullmatch(IP_REGEX, value):
        return "ip"
    if value.startswith("http://") or value.startswith("https://"):
        return "url"
    if re.fullmatch(DOMAIN_REGEX, value):
        return "domain"
    if "@" in value and re.fullmatch(EMAIL_REGEX, value):
        return "email"
    if re.fullmatch(HASH_REGEX, value):
        return "hash"
    return "unknown"

# ========================================================
# 5. FREETEXT PARSER
# ========================================================

def parse_freetext(feed, raw_text: str):
    results = set()
    lines = raw_text.splitlines()

    exclude = None
    if feed.settings.exclude_regex:
        exclude = re.compile(feed.settings.exclude_regex)

    for line in lines:
        if exclude and exclude.search(line):
            continue

        for regex in IOC_REGEXES:
            for match in re.findall(regex, line):
                match = clean_ioc(match)

                # Skip private IP
                if detect_ioc_type(match) == "ip" and is_private_ip(match):
                    continue

                results.add(match)

    return list(results)

# ========================================================
# 6. CSV PARSER
# ========================================================

def parse_csv(feed, raw_text: str):
    results = set()

    reader = csv.reader(
        StringIO(raw_text),
        delimiter=feed.settings.csv_delimiter or ","
    )

    for row in reader:
        for idx in feed.settings.csv_indexes:
            col_index = idx - 1  # config index = 1-based
            if 0 <= col_index < len(row):
                value = clean_ioc(row[col_index])

                if not value:
                    continue

                # Nếu ô CSV chứa nhiều IOC trong một dòng
                extracted = extract_multiple_iocs_from_text(value)

                for ioc in extracted:
                    if detect_ioc_type(ioc) == "ip" and is_private_ip(ioc):
                        continue
                    results.add(ioc)

    return list(results)

# ========================================================
# 7. JSON PARSER (cho feed JSON-based)
# ========================================================

def parse_json_feed(feed, raw_text: str):
    results = set()

    try:
        data = json.loads(raw_text)
    except:
        return []

    # Nếu feed trả list ["1.2.3.4", "5.6.7.8"]
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                results.add(clean_ioc(item))
        return list(results)

    # Nếu dạng {"ioc": "1.2.3.4", "type": "ip"}
    if isinstance(data, dict):
        # Extract toàn bộ string trong dict
        text = json.dumps(data)
        return extract_multiple_iocs_from_text(text)

    return []

# ========================================================
# 8. Helper: bắt nhiều IOC trong 1 dòng
# ========================================================

def extract_multiple_iocs_from_text(text: str):
    found = set()

    for regex in IOC_REGEXES:
        for match in re.findall(regex, text):
            match = clean_ioc(match)
            found.add(match)

    return list(found)

# ========================================================
# 9. Auto Parser — feed.source_format
# ========================================================

def parse_feed(feed, raw_text: str):
    if feed.source_format == "csv":
        return parse_csv(feed, raw_text)

    if feed.source_format == "json":
        return parse_json_feed(feed, raw_text)

    # Mặc định là freetext
    return parse_freetext(feed, raw_text)
