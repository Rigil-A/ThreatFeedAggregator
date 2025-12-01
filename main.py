from core.aggregator import ThreatFeedAggregator

if __name__ == "__main__":
    aggregator = ThreatFeedAggregator()
    all_iocs = aggregator.run_all()

    if all_iocs is None:
        print("[ERROR] aggregator.run_all() returned None")
        exit(1)

    print(f"[✓] Total IOCs: {len(all_iocs)}")
    
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"output/iocs_{timestamp}.csv"
    
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, 
            fieldnames=["value", "type", "source", "severity", "tags", "timestamp"]
        )
        writer.writeheader()
        for ioc in all_iocs:
            writer.writerow(ioc.to_dict())
    
    print(f"[✓] Saved {len(all_iocs)} IOCs to {csv_file}")
    # In 10 IOC đầu tiên
    for ioc in all_iocs[:10]:
        print(ioc.to_dict())