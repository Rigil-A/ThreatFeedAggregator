import requests
import csv
import json
import io
import datetime
import time

# Threat Intelligence Sources
# Structure: "<Source's name>": (URL, Format type, Default IOC type)
FEEDS = {
    "URLhaus": ("https://urlhaus.abuse.ch/downloads/csv_recent/", "csv_abusech", "url"),
    "ThreatFox": ("https://threatfox.abuse.ch/export/json/recent/", "json_threatfox", "mixed"),
    "Feodo_Tracker": ("https://feodotracker.abuse.ch/downloads/ipblocklist.csv", "csv_simple", "ip"),
    "OpenPhish": ("https://openphish.com/feed.txt", "txt", "url"),
    "DigitalSide": ("https://raw.githubusercontent.com/davidonzo/Threat-Intel/master/lists/latesturls.txt", "txt", "url"),
    "CINS_Score": ("http://cinsscore.com/list/ci-badguys.txt", "txt", "ip"),
    "GreenSnow": ("https://blocklist.greensnow.co/greensnow.txt", "txt", "ip"),
    "MalwareBazaar": ("https://bazaar.abuse.ch/export/csv/recent/", "csv_abusech", "hash"),
    "Tor_Exit_Nodes": ("https://check.torproject.org/torbulkexitlist", "txt", "ip"),
    "SSL_Blacklist": ("https://sslbl.abuse.ch/blacklist/sslblacklist.csv", "csv_simple", "ssl_cert")
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; MyThreatAggregator/1.0)'
}

# Normalize IOC data into a common JSON format
def normalize_ioc(source, ioc_type, value, date_added=None):
    if not date_added:
        date_added = datetime.datetime.now().isoformat()
    
    return {
        "source": source,
        "type": ioc_type,
        "value": value.strip(),
        "timestamp": date_added,
        "aggregator_processed_at": datetime.datetime.now().isoformat()
    }

# Analyse different formats
def parse_txt(source, content, default_type):
    results = []
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        # Skip empty lines and comments
        if line and not line.startswith('#'):
            results.append(normalize_ioc(source, default_type, line))
    return results

def parse_csv_abusech(source, content, default_type):
    # Handling Abuse.ch style CSVs
    results = []
    f = io.StringIO(content)
    # abuse.ch CSV often contains comments starting with '#'
    reader = csv.reader(filter(lambda x: not x.startswith('#'), f))
    
    for row in reader:
        if row:
            # depending on source, select appropriate column
            # URLhaus: column 2 (index 2) is the URL. MalwareBazaar: column 1 (index 1) is the sha256
            val = ""
            if source == "URLhaus":
                val = row[2] # url
            elif source == "MalwareBazaar":
                val = row[1] # sha256
            else:
                val = row[0] # Default: take the first column
                
            if val:
                results.append(normalize_ioc(source, default_type, val))
    return results

def parse_csv_simple(source, content, default_type):
    # Handle simple CSV (no complex headers)
    results = []
    f = io.StringIO(content)
    reader = csv.reader(filter(lambda x: not x.startswith('#'), f))
    for row in reader:
        if row:
            results.append(normalize_ioc(source, default_type, row[0])) # Take column 1
    return results

def parse_json_threatfox(source, content, default_type):
    # Handle ThreatFox JSON
    results = []
    try:
        data = json.loads(content)
        # ThreatFox returns a dictionary where the values contain the data
        for item in data.values():
            # ThreatFox JSON structure: [{'ioc_value': '...', 'ioc_type': '...'}]
            # Note: actual structure may be a list of dicts
            if isinstance(item, list):
                 for threat in item:
                     results.append(normalize_ioc(
                         source, 
                         threat.get('ioc_type'), 
                         threat.get('ioc_value'),
                         threat.get('date_added')
                     ))
    except json.JSONDecodeError:
        print(f"[-] Error decoding JSON from {source}")
    return results

# Main fetch function (main logic)
def fetch_all_feeds():
    aggregated_data = []
    print(f"[*] Starting fetch of {len(FEEDS)} feeds...")

    for name, (url, fmt, ioc_type) in FEEDS.items():
        print(f"   -> Downloading: {name}...", end=" ")
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                data = []
                content = response.text
                
                # choose parser based on format config
                if fmt == 'txt':
                    data = parse_txt(name, content, ioc_type)
                elif fmt == 'csv_abusech':
                    data = parse_csv_abusech(name, content, ioc_type)
                elif fmt == 'csv_simple':
                    data = parse_csv_simple(name, content, ioc_type)
                elif fmt == 'json_threatfox':
                    data = parse_json_threatfox(name, content, ioc_type)
                
                print(f"OK! Retrieved {len(data)} IOCs.")
                aggregated_data.extend(data)
            else:
                print(f"HTTP Error {response.status_code}")
        except Exception as e:
            print(f"Exception: {e}")

    # Save results
    output_file = 'aggregated_threats.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(aggregated_data, f, indent=4)
    
    print(f"\n[DONE] Total: {len(aggregated_data)} IOCs saved to '{output_file}'")

if __name__ == "__main__":
    fetch_all_feeds()