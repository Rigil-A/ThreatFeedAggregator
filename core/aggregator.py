from utils.config_loader import load_feeds
from feeds.downloader import fetch_feed
from feeds.parser import parse_feed
from core.ioc_normalizer import normalize_bulk

class ThreatFeedAggregator:
    def __init__(self):
        self.feeds = load_feeds()

    def process_feed(self, feed):
        """
        Tải → Parse → Normalize → Trả về list IOC (IOC objects)
        """
        print(f"[+] Processing feed: {feed.name}")

        try:
            # Step 1: download
            raw_data = fetch_feed(feed)
        except Exception as e:
            print(f"[ERROR] Download failed for {feed.name}: {e}")
            return []

        try:
            # Step 2: parse raw IOC values
            raw_iocs = parse_feed(feed, raw_data)
        except Exception as e:
            print(f"[ERROR] Parsing failed for {feed.name}: {e}")
            return []

        try:
            # Step 3: normalize IOC objects
            normalized = normalize_bulk(raw_iocs, feed)
        except Exception as e:
            print(f"[ERROR] Normalization failed for {feed.name}: {e}")
            return []

        print(f"[+] {feed.name}: {len(normalized)} IOCs extracted & normalized")
        return normalized



    def run_all(self):
        
        print(f"[DEBUG] Found {len(self.feeds)} feeds in config")
        for feed in self.feeds:
            print(f"  - {feed.name}: enabled={feed.enabled}, url={feed.url}")
        
        all_iocs = []
        for feed in self.feeds:
            if not feed.enabled:
                print(f"[SKIP] {feed.name} is disabled")
                continue
            # ...existing code...
            all_iocs = []
            
            for feed in self.feeds:
                if not feed.enabled:
                    print(f"[SKIP] {feed.name} is disabled")
                    continue

                iocs = self.process_feed(feed)
                all_iocs.extend(iocs)

            print(f"\n[✓] Aggregator completed: {len(all_iocs)} total IOCs.")
            return all_iocs
