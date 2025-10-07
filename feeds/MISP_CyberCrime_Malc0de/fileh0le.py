import csv, ipaddress, datetime
src = "https://iplists.firehol.org/files/firehol_level1.ipset"
fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
with open("firehol_level1.ipset") as f, open("firehol_level1.csv","w",newline="",encoding="utf-8") as out:
    writer = csv.DictWriter(out, fieldnames=["value","type","source","fetched_at"])
    writer.writeheader()
    for line in f:
        s=line.strip()
        if not s or s.startswith('#'):
            continue
        try:
            ipaddress.ip_network(s)
            t = "network"
        except Exception:
            t = "unknown"
        writer.writerow({"value":s,"type":t,"source":src,"fetched_at":fetched_at})
