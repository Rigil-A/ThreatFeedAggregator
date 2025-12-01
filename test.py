from core.db import create_table, add_ioc, filter_iocs, delete_iocs

data = filter_iocs(first_from="2025-10-07 14:41:03", first_to="2025-10-07 14:41:03", last_to="2025-10-07 14:43:05")
for row in data:
    print(row)