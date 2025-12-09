import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List
from models.ioc import IOC
from typing import Optional

class IOCExporter:
    """Export IOCs to multiple formats (CSV, JSON, TXT, JSONL, SQLite)"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def export_csv(self, iocs: List[IOC], filename: str = None) -> str:
        """Export IOCs to CSV format"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"iocs_{timestamp}.csv"

        filepath = self.output_dir / filename

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['value', 'type', 'source', 'feed_name', 'metadata', 'timestamp'])
            writer.writeheader()
            for ioc in iocs:
                writer.writerow({
                    'value': ioc.value,
                    'type': ioc.ioc_type,
                    'source': ioc.source,
                    'feed_name': ioc.feed_name,
                    'metadata': json.dumps(ioc.metadata),
                    'timestamp': datetime.now().isoformat()
                })
        return str(filepath)

    def export_json(self, iocs: List[IOC], filename: str = None) -> str:
        """Export IOCs to JSON format"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"iocs_{timestamp}.json"

        filepath = self.output_dir / filename

        data = [
            {
                'value': ioc.value,
                'type': ioc.ioc_type,
                'source': ioc.source,
                'feed_name': ioc.feed_name,
                'metadata': ioc.metadata
            }
            for ioc in iocs
        ]

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return str(filepath)

    def export_txt(self, iocs: List[IOC], filename: str = None) -> str:
        """Export IOCs as plain text (one per line)"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"iocs_{timestamp}.txt"

        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            for ioc in iocs:
                f.write(f"{ioc.value}\n")

        return str(filepath)

    def export_jsonl(self, iocs: List[IOC], filename: str = None) -> str:
        """Export IOCs as JSON Lines (one JSON object per line)"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"iocs_{timestamp}.jsonl"

        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            for ioc in iocs:
                obj = {
                    'value': ioc.value,
                    'type': ioc.ioc_type,
                    'source': ioc.source,
                    'feed_name': ioc.feed_name,
                    'metadata': ioc.metadata,
                    'timestamp': datetime.now().isoformat()
                }
                f.write(json.dumps(obj, ensure_ascii=False) + '\\n')

        return str(filepath)

    def export_sqlite(self, iocs: List[IOC], filename: str = None, table_name: str = 'iocs') -> str:
        """Export IOCs into a SQLite database (single table)."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"iocs_{timestamp}.sqlite"

        filepath = self.output_dir / filename

        conn = sqlite3.connect(str(filepath))
        cur = conn.cursor()

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value TEXT,
            type TEXT,
            source TEXT,
            feed_name TEXT,
            metadata TEXT,
            timestamp TEXT
        )
        """)

        insert_sql = f"INSERT INTO {table_name} (value, type, source, feed_name, metadata, timestamp) VALUES (?, ?, ?, ?, ?, ?)"

        now = datetime.now().isoformat()
        rows = [
            (ioc.value, ioc.ioc_type, ioc.source, ioc.feed_name, json.dumps(ioc.metadata, ensure_ascii=False), now)
            for ioc in iocs
        ]

        cur.executemany(insert_sql, rows)
        conn.commit()
        conn.close()

        return str(filepath)

    def export_all_formats(self, iocs: List[IOC], base_filename: str = None) -> dict:
        """Export to CSV, JSON, TXT, JSONL and SQLite simultaneously"""
        if not base_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"iocs_{timestamp}"

        results = {
            'csv': self.export_csv(iocs, f"{base_filename}.csv"),
            'json': self.export_json(iocs, f"{base_filename}.json"),
            'txt': self.export_txt(iocs, f"{base_filename}.txt"),
            'jsonl': self.export_jsonl(iocs, f"{base_filename}.jsonl"),
            'sqlite': self.export_sqlite(iocs, f"{base_filename}.sqlite")
        }

        return results

    def load_iocs_from_db(self, db_path: Optional[str] = None, table_name: str = 'indicators', sql: Optional[str] = None) -> List[IOC]:
        """Load IOCs from an SQLite DB and return as List[IOC].

        - `db_path`: path to sqlite file (defaults to `data/database/ioc_database.db`).
        - `table_name`: table to read from when `sql` is not provided (default `indicators`).
        - `sql`: optional custom SQL query to run instead of selecting the table.
        - `filters`: reserved for future filtering support (currently unused).

        This loader is flexible: it maps common column names (`ioc_value`/`value`, `ioc_type`/`type`,
        `source`, `feed_name`, `metadata`, `first_seen`, `last_seen`) into the `IOC` model. If a
        `metadata` column exists and contains JSON text, it will be parsed.
        """
        if not db_path:
            db_path = "data/database/ioc_database.db"

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Use custom SQL if provided, otherwise select all from the requested table
        if sql:
            query = sql
        else:
            query = f"SELECT * FROM {table_name}"

        try:
            cur.execute(query)
        except Exception:
            conn.close()
            raise

        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description] if cur.description else []
        conn.close()

        iocs: List[IOC] = []
        for row in rows:
            row_map = dict(zip(col_names, row)) if col_names else {}

            # tolerant field lookup
            val = row_map.get('ioc_value') or row_map.get('value') or row_map.get('indicator') or row_map.get('ioc')
            typ = row_map.get('ioc_type') or row_map.get('type')
            src = row_map.get('source') or row_map.get('feed')
            feed_name = row_map.get('feed_name') or row_map.get('feed_name') or row_map.get('feed')

            # metadata: prefer an explicit metadata column, fallback to first/last seen
            metadata = {}
            raw_meta = row_map.get('metadata')
            if raw_meta:
                if isinstance(raw_meta, (str, bytes)):
                    try:
                        metadata = json.loads(raw_meta)
                    except Exception:
                        metadata = {"raw": raw_meta}
                else:
                    metadata = raw_meta
            else:
                first_seen = row_map.get('first_seen') or row_map.get('first_seen_ts')
                last_seen = row_map.get('last_seen') or row_map.get('last_seen_ts')
                if first_seen or last_seen:
                    metadata = {"first_seen": first_seen, "last_seen": last_seen}

            if not val:
                # skip rows without a value we can map
                continue

            iocs.append(IOC(value=val, ioc_type=typ, source=src, feed_name=feed_name, metadata=metadata))

        return iocs

    def export_from_db(self, fmt: str = 'csv', db_path: Optional[str] = None, filename: Optional[str] = None, **kwargs) -> str:
        """Read IOCs from the DB and export to desired format.
        - `fmt`: one of 'csv','json','txt','jsonl','sqlite'
        - `db_path`: optional path to sqlite DB
        - `filename`: optional output filename
        - additional kwargs are passed to underlying exporter methods
        Returns path to exported file (or dict when exporting all formats).
        """
        iocs = self.load_iocs_from_db(db_path=db_path)

        fmt = fmt.lower()
        if fmt == 'csv':
            return self.export_csv(iocs, filename)
        if fmt == 'json':
            return self.export_json(iocs, filename)
        if fmt == 'txt':
            return self.export_txt(iocs, filename)
        if fmt == 'jsonl':
            return self.export_jsonl(iocs, filename)
        if fmt == 'sqlite':
            return self.export_sqlite(iocs, filename, table_name=kwargs.get('table_name', 'iocs'))

        # export all supported formats and return mapping
        if fmt == 'all':
            base = filename if filename else None
            return self.export_all_formats(iocs, base_filename=base)

        # unsupported -> raise
        raise ValueError(f"Unsupported export format: {fmt}")