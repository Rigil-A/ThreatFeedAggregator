import sqlite3
from core import db

class IOCEnricher:
    """
    Lớp thực hiện enrich cho các loại IoC: hash, ip, domain, url.
    Kết nối với DB, sử dụng các hàm insert/query enrich info đã có.
    """
    def __init__(self, db_path=None):
        self.db_path = db_path or db.DB_PATH
        self.conn = sqlite3.connect(self.db_path)

    def enrich_hash(self, ioc_id, enrich_data):
        """Enrich hash IoC và lưu vào DB."""
        return db.insert_hash_enrich_info(ioc_id, enrich_data, conn=self.conn)

    def enrich_ip(self, ioc_id, enrich_data):
        """Enrich IP IoC và lưu vào DB."""
        return db.insert_ip_enrich_info(ioc_id, enrich_data, conn=self.conn)

    def enrich_domain(self, ioc_id, enrich_data):
        """Enrich domain IoC và lưu vào DB."""
        return db.insert_domain_enrich_info(ioc_id, enrich_data, conn=self.conn)

    def enrich_url(self, ioc_id, enrich_data):
        """Enrich URL IoC và lưu vào DB."""
        return db.insert_url_enrich_info(ioc_id, enrich_data, conn=self.conn)

    def get_hash_enrich(self, **filters):
        """Lấy enrich info cho hash với filter."""
        return db.get_hash_enrich_info(conn=self.conn, **filters)

    def get_ip_enrich(self, **filters):
        """Lấy enrich info cho ip với filter."""
        return db.get_ip_enrich_info(conn=self.conn, **filters)

    def get_domain_enrich(self, **filters):
        """Lấy enrich info cho domain với filter."""
        return db.get_domain_enrich_info(conn=self.conn, **filters)

    def get_url_enrich(self, **filters):
        """Lấy enrich info cho url với filter."""
        return db.get_url_enrich_info(conn=self.conn, **filters)

    def close(self):
        if self.conn:
            self.conn.close()

# Ví dụ sử dụng
if __name__ == "__main__":
    enricher = IOCEnricher()
    # enrich_hash, enrich_ip, enrich_domain, enrich_url
    # get_hash_enrich, get_ip_enrich, get_domain_enrich, get_url_enrich
    enricher.close()
