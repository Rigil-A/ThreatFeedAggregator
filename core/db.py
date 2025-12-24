import sqlite3
from datetime import datetime

DB_PATH = "data/database/ioc_database.db"

def create_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Bật hỗ trợ khóa ngoại
    c.execute("PRAGMA foreign_keys = ON;")

    # Bảng fetch_history
    c.execute("""
        CREATE TABLE IF NOT EXISTS fetch_history (
            fetch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_src INTEGER,
            total_ioc INTEGER,
            new_ioc INTEGER,
            fetch_at TEXT
        )
    """)

    # Bảng ioc
    c.execute("""
        CREATE TABLE IF NOT EXISTS ioc (
            ioc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ioc_value TEXT NOT NULL,
            ioc_type TEXT NOT NULL,
            ioc_score REAL,
            is_enriched INTEGER DEFAULT 0,
            first_fetch_id INTEGER,
            last_fetch_id INTEGER,
            FOREIGN KEY (first_fetch_id) REFERENCES fetch_history(fetch_id),
            FOREIGN KEY (last_fetch_id) REFERENCES fetch_history(fetch_id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_ioc_value_type ON ioc(ioc_value, ioc_type)")

    # Bảng hash_detail
    c.execute("""
        CREATE TABLE IF NOT EXISTS hash_detail (
            hash_enrich_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ioc_id INTEGER NOT NULL,
            last_enrich TEXT,
            file_type TEXT,
            file_size INTEGER,
            malware_family TEXT,
            threat_label TEXT,
            av_detection_ratio TEXT,
            ssdeep TEXT,
            tlsh TEXT,
            imphash TEXT,
            rich_pe TEXT,
            sig_check TEXT,
            pe_sections TEXT,
            related_domains TEXT,
            related_ips TEXT,
            sandbox_behavior TEXT,
            signature_info TEXT,
            download_urls TEXT,
            FOREIGN KEY (ioc_id) REFERENCES ioc(ioc_id)
        )
    """)

    # Bảng ip_detail
    c.execute("""
        CREATE TABLE IF NOT EXISTS ip_detail (
            ip_enrich_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ioc_id INTEGER NOT NULL,
            last_enrich TEXT,
            asm TEXT,
            isp TEXT,
            org TEXT,
            loc TEXT,
            is_vpn INTEGER,
            is_proxy INTEGER,
            is_hosting INTEGER,
            is_tor INTEGER,
            reputation_score REAL,
            total_reports INTEGER,
            tags TEXT,
            open_ports TEXT,
            services TEXT,
            is_malware_c2 INTEGER,
            passive_dns TEXT,
            FOREIGN KEY (ioc_id) REFERENCES ioc(ioc_id)
        )
    """)

    # Bảng domain_detail
    c.execute("""
        CREATE TABLE IF NOT EXISTS domain_detail (
            domain_enrich_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ioc_id INTEGER NOT NULL,
            last_enrich TEXT,
            registrar TEXT,
            registrant TEXT,
            create_date TEXT,
            expire_date TEXT,
            dns_record TEXT,
            spf TEXT,
            dkim TEXT,
            dmarc TEXT,
            passive_dns TEXT,
            category TEXT,
            reputation_score REAL,
            related_hashes TEXT,
            hosting_provider TEXT,
            ssl_issuer TEXT,
            ssl_valid_from TEXT,
            ssl_valid_to TEXT,
            FOREIGN KEY (ioc_id) REFERENCES ioc(ioc_id)
        )
    """)

    # Bảng url_detail
    c.execute("""
        CREATE TABLE IF NOT EXISTS url_detail (
            url_enrich_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ioc_id INTEGER NOT NULL,
            last_enrich TEXT,
            final_url TEXT,
            http_status TEXT,
            content_type TEXT,
            page_title TEXT,
            screenshot TEXT,
            malware_family TEXT,
            reputation_score REAL,
            payload_hash TEXT,
            is_phishing INTEGER,
            redirect_chain TEXT,
            FOREIGN KEY (ioc_id) REFERENCES ioc(ioc_id)
        )
    """)

    conn.commit()
    conn.close()

def insert_fetch_history(total_src, total_ioc, new_ioc, fetch_at=None):
    """
    Thêm một bản ghi mới vào bảng Fetch_History cho mỗi lượt fetch.
    Args:
        total_src: Tổng số nguồn
        total_ioc: Tổng số IoC
        new_ioc: Số lượng IoC mới
        fetch_at: Thời điểm fetch (nếu None sẽ lấy thời gian hiện tại)
    Returns:
        fetch_id: Id của bản ghi vừa tạo
    """
    if fetch_at is None:
        fetch_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Reset toàn bộ ioc_score về 0 trước khi thêm lượt fetch mới
    c.execute("UPDATE ioc SET ioc_score = 0")
    # Thêm bản ghi fetch mới
    c.execute("""
        INSERT INTO fetch_history (total_src, total_ioc, new_ioc, fetch_at)
        VALUES (?, ?, ?, ?)
    """, (total_src, total_ioc, new_ioc, fetch_at))
    fetch_id = c.lastrowid
    conn.commit()
    conn.close()
    return fetch_id

def update_fetch_history(fetch_id, total_src=None, total_ioc=None, new_ioc=None):
    """
    Cập nhật các trường total_src, total_ioc, new_ioc cho một bản ghi fetch_history.
    Args:
        fetch_id: id của bản ghi fetch_history cần cập nhật
        total_src, total_ioc, new_ioc: giá trị mới (nếu None sẽ giữ nguyên)
    Returns:
        True nếu thành công, False nếu không có gì cập nhật hoặc lỗi.
    """
    fields = []
    values = []
    if total_src is not None:
        fields.append("total_src = ?")
        values.append(total_src)
    if total_ioc is not None:
        fields.append("total_ioc = ?")
        values.append(total_ioc)
    if new_ioc is not None:
        fields.append("new_ioc = ?")
        values.append(new_ioc)
    if not fields:
        return False
    values.append(fetch_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(f"UPDATE fetch_history SET {', '.join(fields)} WHERE fetch_id = ?", values)
        conn.commit()
        return c.rowcount > 0
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()

def add_ioc(ioc_value, ioc_type, fetch_id, conn=None):
    """
    Thêm hoặc cập nhật một IOC vào database.
    Args:
        ioc_value: Giá trị IOC
        ioc_type: Loại IOC
        fetch_id: Id của lượt fetch hiện tại
        conn: Connection SQLite tùy chọn. Nếu None, sẽ tự tạo và đóng connection.
    Returns:
        1 nếu thêm mới, 0 nếu cập nhật, -1 nếu lỗi
    """
    should_close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        should_close = True

    try:
        c = conn.cursor()
        # Kiểm tra xem IoC đã tồn tại chưa (theo ioc_value và ioc_type)
        c.execute("SELECT ioc_id, ioc_score FROM ioc WHERE ioc_value = ? AND ioc_type = ?", (ioc_value, ioc_type))
        existing = c.fetchone()

        if existing:
            # Nếu đã tồn tại -> tăng ioc_score lên 1, cập nhật last_fetch_id
            new_score = (existing[1] or 0) + 1
            c.execute("UPDATE ioc SET last_fetch_id = ?, ioc_score = ? WHERE ioc_id = ?", (fetch_id, new_score, existing[0]))
            result = 0
        else:
            # Nếu chưa tồn tại -> thêm mới, score = 1
            c.execute("""
                INSERT INTO ioc (ioc_value, ioc_type, first_fetch_id, last_fetch_id, is_enriched, ioc_score)
                VALUES (?, ?, ?, ?, 0, 1)
            """, (ioc_value, ioc_type, fetch_id, fetch_id))
            result = 1

        if should_close:
            conn.commit()
            conn.close()
        return result
    except Exception:
        if should_close:
            conn.rollback()
            conn.close()
        return -1

def add_iocs_batch(iocs_list, fetch_id):
    """
    Batch insert/update nhiều IoC vào DB, chỉ nhận ioc_value và ioc_type.
    Args:
        iocs_list: list các dict {'ioc_value':..., 'ioc_type':...}
        fetch_id: id của lượt fetch hiện tại
    Returns:
        Số lượng IoC mới được thêm
    """
    if not iocs_list:
        return 0

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA synchronous=NORMAL;")
        c.execute("PRAGMA cache_size=-64000;")
    except Exception:
        pass

    written = 0
    try:
        # Chuẩn hóa danh sách IoC
        unique_keys = set()
        for ioc in iocs_list:
            ioc_value = ioc.get("ioc_value")
            ioc_type = ioc.get("ioc_type")
            if ioc_value and ioc_type:
                unique_keys.add((ioc_value, ioc_type))

        # Lấy các IoC đã tồn tại
        existing_map = {}
        if unique_keys:
            chunk_size = 500
            unique_keys_list = list(unique_keys)
            for i in range(0, len(unique_keys_list), chunk_size):
                chunk = unique_keys_list[i:i + chunk_size]
                conditions = []
                values = []
                for key in chunk:
                    conditions.append("(ioc_value = ? AND ioc_type = ?)")
                    values.extend(key)
                query = "SELECT ioc_id, ioc_value, ioc_type, ioc_score FROM ioc WHERE " + " OR ".join(conditions)
                c.execute(query, values)
                for row in c.fetchall():
                    existing_map[(row[1], row[2])] = (row[0], row[3])

        # Batch xử lý
        for ioc_value, ioc_type in unique_keys:
            exist = existing_map.get((ioc_value, ioc_type))
            if exist:
                ioc_id, old_score = exist
                new_score = (old_score or 0) + 1
                c.execute("UPDATE ioc SET last_fetch_id = ?, ioc_score = ? WHERE ioc_id = ?", (fetch_id, new_score, ioc_id))
            else:
                c.execute("INSERT INTO ioc (ioc_value, ioc_type, first_fetch_id, last_fetch_id, is_enriched, ioc_score) VALUES (?, ?, ?, ?, 0, 1)", (ioc_value, ioc_type, fetch_id, fetch_id))
                written += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return written

def filter_iocs(
    ioc_value=None,
    ioc_type=None,
    first_fetch_id=None,
    last_fetch_id=None,
    min_score=None,
    max_score=None,
    is_enriched=None
):
    """
    Lọc IoC theo các thuộc tính cho trước trên bảng ioc.
    Args:
        ioc_value, ioc_type: giá trị chuỗi hoặc None
        first_fetch_id, last_fetch_id: lọc theo id lượt fetch
        min_score, max_score: lọc theo khoảng score
        is_enriched: 0/1 hoặc None
    Returns:
        List các bản ghi phù hợp
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = "SELECT * FROM ioc WHERE 1=1"
    params = []
    if ioc_value not in (None, ""):
        query += " AND ioc_value = ?"
        params.append(ioc_value)
    if ioc_type not in (None, ""):
        query += " AND ioc_type = ?"
        params.append(ioc_type)
    if first_fetch_id is not None:
        query += " AND first_fetch_id = ?"
        params.append(first_fetch_id)
    if last_fetch_id is not None:
        query += " AND last_fetch_id = ?"
        params.append(last_fetch_id)
    if min_score is not None:
        query += " AND ioc_score >= ?"
        params.append(min_score)
    if max_score is not None:
        query += " AND ioc_score <= ?"
        params.append(max_score)
    if is_enriched is not None:
        query += " AND is_enriched = ?"
        params.append(is_enriched)
    query += " ORDER BY ioc_score DESC, ioc_id DESC"
    c.execute(query, params)
    results = c.fetchall()
    conn.close()
    return results

def delete_iocs(
    ioc_value=None,
    ioc_type=None,
    first_fetch_id=None,
    last_fetch_id=None,
    min_score=None,
    max_score=None,
    is_enriched=None
):
    """
    Xóa IoC theo các thuộc tính cho trước trên bảng ioc.
    Args:
        ioc_value, ioc_type: giá trị chuỗi hoặc None
        first_fetch_id, last_fetch_id: lọc theo id lượt fetch
        min_score, max_score: lọc theo khoảng score
        is_enriched: 0/1 hoặc None
    Returns:
        Số hàng đã bị xóa
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = "DELETE FROM ioc WHERE 1=1"
    params = []
    if ioc_value not in (None, ""):
        query += " AND ioc_value = ?"
        params.append(ioc_value)
    if ioc_type not in (None, ""):
        query += " AND ioc_type = ?"
        params.append(ioc_type)
    if first_fetch_id is not None:
        query += " AND first_fetch_id = ?"
        params.append(first_fetch_id)
    if last_fetch_id is not None:
        query += " AND last_fetch_id = ?"
        params.append(last_fetch_id)
    if min_score is not None:
        query += " AND ioc_score >= ?"
        params.append(min_score)
    if max_score is not None:
        query += " AND ioc_score <= ?"
        params.append(max_score)
    if is_enriched is not None:
        query += " AND is_enriched = ?"
        params.append(is_enriched)
    c.execute(query, params)
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected  # Trả về số hàng đã bị xóa

# --- ENRICH INSERT FUNCTIONS ---
def insert_hash_enrich_info(ioc_id, enrich_data, conn=None):
    """
    Thêm enrich cho hash IoC. enrich_data là dict các trường của bảng hash_detail.
    """
    should_close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        should_close = True
    c = conn.cursor()
    fields = ["ioc_id"] + list(enrich_data.keys())
    values = [ioc_id] + list(enrich_data.values())
    query = f"INSERT INTO hash_detail ({', '.join(fields)}) VALUES ({', '.join(['?']*len(fields))})"
    c.execute(query, values)
    if should_close:
        conn.commit()
        conn.close()
    return c.lastrowid

def insert_ip_enrich_info(ioc_id, enrich_data, conn=None):
    should_close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        should_close = True
    c = conn.cursor()
    fields = ["ioc_id"] + list(enrich_data.keys())
    values = [ioc_id] + list(enrich_data.values())
    query = f"INSERT INTO ip_detail ({', '.join(fields)}) VALUES ({', '.join(['?']*len(fields))})"
    c.execute(query, values)
    if should_close:
        conn.commit()
        conn.close()
    return c.lastrowid

def insert_domain_enrich_info(ioc_id, enrich_data, conn=None):
    should_close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        should_close = True
    c = conn.cursor()
    fields = ["ioc_id"] + list(enrich_data.keys())
    values = [ioc_id] + list(enrich_data.values())
    query = f"INSERT INTO domain_detail ({', '.join(fields)}) VALUES ({', '.join(['?']*len(fields))})"
    c.execute(query, values)
    if should_close:
        conn.commit()
        conn.close()
    return c.lastrowid

def insert_url_enrich_info(ioc_id, enrich_data, conn=None):
    should_close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        should_close = True
    c = conn.cursor()
    fields = ["ioc_id"] + list(enrich_data.keys())
    values = [ioc_id] + list(enrich_data.values())
    query = f"INSERT INTO url_detail ({', '.join(fields)}) VALUES ({', '.join(['?']*len(fields))})"
    c.execute(query, values)
    if should_close:
        conn.commit()
        conn.close()
    return c.lastrowid

# --- ENRICH QUERY FUNCTIONS ---
def get_hash_enrich_info(
        ioc_id=None,
        last_enrich=None,
        file_type=None,
        malware_family=None,
        threat_label=None,
        min_file_size=None,
        max_file_size=None,
        av_detection_ratio=None,
        conn=None
    ):
        """
        Lấy enrich info cho hash với nhiều filter.
        """
        should_close = False
        if conn is None:
            conn = sqlite3.connect(DB_PATH)
            should_close = True
        c = conn.cursor()
        query = "SELECT * FROM hash_detail WHERE 1=1"
        params = []
        if ioc_id is not None:
            query += " AND ioc_id = ?"
            params.append(ioc_id)
        if last_enrich is not None:
            query += " AND last_enrich = ?"
            params.append(last_enrich)
        if file_type is not None:
            query += " AND file_type = ?"
            params.append(file_type)
        if malware_family is not None:
            query += " AND malware_family = ?"
            params.append(malware_family)
        if threat_label is not None:
            query += " AND threat_label = ?"
            params.append(threat_label)
        if min_file_size is not None:
            query += " AND file_size >= ?"
            params.append(min_file_size)
        if max_file_size is not None:
            query += " AND file_size <= ?"
            params.append(max_file_size)
        if av_detection_ratio is not None:
            query += " AND av_detection_ratio = ?"
            params.append(av_detection_ratio)
        query += " ORDER BY hash_enrich_id DESC"
        c.execute(query, params)
        result = c.fetchall()
        if should_close:
            conn.close()
        return result

def get_ip_enrich_info(
        ioc_id=None,
        last_enrich=None,
        asm=None,
        isp=None,
        org=None,
        loc=None,
        is_vpn=None,
        is_proxy=None,
        is_hosting=None,
        is_tor=None,
        min_reputation_score=None,
        max_reputation_score=None,
        min_total_reports=None,
        max_total_reports=None,
        tags=None,
        open_ports=None,
        services=None,
        is_malware_c2=None,
        conn=None
    ):
        """
        Lấy enrich info cho ip với nhiều filter.
        """
        should_close = False
        if conn is None:
            conn = sqlite3.connect(DB_PATH)
            should_close = True
        c = conn.cursor()
        query = "SELECT * FROM ip_detail WHERE 1=1"
        params = []
        if ioc_id is not None:
            query += " AND ioc_id = ?"
            params.append(ioc_id)
        if last_enrich is not None:
            query += " AND last_enrich = ?"
            params.append(last_enrich)
        if asm is not None:
            query += " AND asm = ?"
            params.append(asm)
        if isp is not None:
            query += " AND isp = ?"
            params.append(isp)
        if org is not None:
            query += " AND org = ?"
            params.append(org)
        if loc is not None:
            query += " AND loc = ?"
            params.append(loc)
        if is_vpn is not None:
            query += " AND is_vpn = ?"
            params.append(is_vpn)
        if is_proxy is not None:
            query += " AND is_proxy = ?"
            params.append(is_proxy)
        if is_hosting is not None:
            query += " AND is_hosting = ?"
            params.append(is_hosting)
        if is_tor is not None:
            query += " AND is_tor = ?"
            params.append(is_tor)
        if min_reputation_score is not None:
            query += " AND reputation_score >= ?"
            params.append(min_reputation_score)
        if max_reputation_score is not None:
            query += " AND reputation_score <= ?"
            params.append(max_reputation_score)
        if min_total_reports is not None:
            query += " AND total_reports >= ?"
            params.append(min_total_reports)
        if max_total_reports is not None:
            query += " AND total_reports <= ?"
            params.append(max_total_reports)
        if tags is not None:
            query += " AND tags = ?"
            params.append(tags)
        if open_ports is not None:
            query += " AND open_ports = ?"
            params.append(open_ports)
        if services is not None:
            query += " AND services = ?"
            params.append(services)
        if is_malware_c2 is not None:
            query += " AND is_malware_c2 = ?"
            params.append(is_malware_c2)
        query += " ORDER BY ip_enrich_id DESC"
        c.execute(query, params)
        result = c.fetchall()
        if should_close:
            conn.close()
        return result

def get_domain_enrich_info(
        ioc_id=None,
        last_enrich=None,
        registrar=None,
        registrant=None,
        create_date=None,
        expire_date=None,
        dns_record=None,
        spf=None,
        dkim=None,
        dmarc=None,
        passive_dns=None,
        category=None,
        min_reputation_score=None,
        max_reputation_score=None,
        related_hashes=None,
        hosting_provider=None,
        ssl_issuer=None,
        ssl_valid_from=None,
        ssl_valid_to=None,
        conn=None
    ):
        """
        Lấy enrich info cho domain với nhiều filter.
        """
        should_close = False
        if conn is None:
            conn = sqlite3.connect(DB_PATH)
            should_close = True
        c = conn.cursor()
        query = "SELECT * FROM domain_detail WHERE 1=1"
        params = []
        if ioc_id is not None:
            query += " AND ioc_id = ?"
            params.append(ioc_id)
        if last_enrich is not None:
            query += " AND last_enrich = ?"
            params.append(last_enrich)
        if registrar is not None:
            query += " AND registrar = ?"
            params.append(registrar)
        if registrant is not None:
            query += " AND registrant = ?"
            params.append(registrant)
        if create_date is not None:
            query += " AND create_date = ?"
            params.append(create_date)
        if expire_date is not None:
            query += " AND expire_date = ?"
            params.append(expire_date)
        if dns_record is not None:
            query += " AND dns_record = ?"
            params.append(dns_record)
        if spf is not None:
            query += " AND spf = ?"
            params.append(spf)
        if dkim is not None:
            query += " AND dkim = ?"
            params.append(dkim)
        if dmarc is not None:
            query += " AND dmarc = ?"
            params.append(dmarc)
        if passive_dns is not None:
            query += " AND passive_dns = ?"
            params.append(passive_dns)
        if category is not None:
            query += " AND category = ?"
            params.append(category)
        if min_reputation_score is not None:
            query += " AND reputation_score >= ?"
            params.append(min_reputation_score)
        if max_reputation_score is not None:
            query += " AND reputation_score <= ?"
            params.append(max_reputation_score)
        if related_hashes is not None:
            query += " AND related_hashes = ?"
            params.append(related_hashes)
        if hosting_provider is not None:
            query += " AND hosting_provider = ?"
            params.append(hosting_provider)
        if ssl_issuer is not None:
            query += " AND ssl_issuer = ?"
            params.append(ssl_issuer)
        if ssl_valid_from is not None:
            query += " AND ssl_valid_from = ?"
            params.append(ssl_valid_from)
        if ssl_valid_to is not None:
            query += " AND ssl_valid_to = ?"
            params.append(ssl_valid_to)
        query += " ORDER BY domain_enrich_id DESC"
        c.execute(query, params)
        result = c.fetchall()
        if should_close:
            conn.close()
        return result

def get_url_enrich_info(
        ioc_id=None,
        last_enrich=None,
        final_url=None,
        http_status=None,
        content_type=None,
        page_title=None,
        screenshot=None,
        malware_family=None,
        min_reputation_score=None,
        max_reputation_score=None,
        payload_hash=None,
        is_phishing=None,
        redirect_chain=None,
        conn=None
    ):
        """
        Lấy enrich info cho url với nhiều filter.
        """
        should_close = False
        if conn is None:
            conn = sqlite3.connect(DB_PATH)
            should_close = True
        c = conn.cursor()
        query = "SELECT * FROM url_detail WHERE 1=1"
        params = []
        if ioc_id is not None:
            query += " AND ioc_id = ?"
            params.append(ioc_id)
        if last_enrich is not None:
            query += " AND last_enrich = ?"
            params.append(last_enrich)
        if final_url is not None:
            query += " AND final_url = ?"
            params.append(final_url)
        if http_status is not None:
            query += " AND http_status = ?"
            params.append(http_status)
        if content_type is not None:
            query += " AND content_type = ?"
            params.append(content_type)
        if page_title is not None:
            query += " AND page_title = ?"
            params.append(page_title)
        if screenshot is not None:
            query += " AND screenshot = ?"
            params.append(screenshot)
        if malware_family is not None:
            query += " AND malware_family = ?"
            params.append(malware_family)
        if min_reputation_score is not None:
            query += " AND reputation_score >= ?"
            params.append(min_reputation_score)
        if max_reputation_score is not None:
            query += " AND reputation_score <= ?"
            params.append(max_reputation_score)
        if payload_hash is not None:
            query += " AND payload_hash = ?"
            params.append(payload_hash)
        if is_phishing is not None:
            query += " AND is_phishing = ?"
            params.append(is_phishing)
        if redirect_chain is not None:
            query += " AND redirect_chain = ?"
            params.append(redirect_chain)
        query += " ORDER BY url_enrich_id DESC"
        c.execute(query, params)
        result = c.fetchall()
        if should_close:
            conn.close()
        return result

if __name__ == "__main__":
    create_tables()