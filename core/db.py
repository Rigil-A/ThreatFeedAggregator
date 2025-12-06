import sqlite3
from datetime import datetime

DB_PATH = "data/database/ioc_database.db"

def create_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ioc_value TEXT NOT NULL,
            ioc_type TEXT NOT NULL,
            source TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
    """)
    # Tạo index để tối ưu truy vấn SELECT/UPDATE theo (ioc_value, ioc_type)
    c.execute("CREATE INDEX IF NOT EXISTS idx_indicators_value_type ON indicators(ioc_value, ioc_type)")
    conn.commit()
    conn.close()

def add_ioc(ioc_value, ioc_type, source, conn=None):
    """
    Thêm hoặc cập nhật một IOC vào database.
    
    Args:
        ioc_value: Giá trị IOC
        ioc_type: Loại IOC
        source: Nguồn IOC
        conn: Connection SQLite tùy chọn. Nếu None, sẽ tự tạo và đóng connection.
              Nếu được cung cấp, sẽ không commit và không đóng connection (để batch commit).
    
    Returns:
        True nếu thành công
    """
    should_close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        should_close = True
    
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Kiểm tra xem IoC đã tồn tại chưa
    c.execute("SELECT id FROM indicators WHERE ioc_value = ? AND ioc_type = ?", (ioc_value, ioc_type))
    existing = c.fetchone()
    
    if existing:
        # Nếu đã tồn tại -> cập nhật last_seen
        c.execute("UPDATE indicators SET last_seen = ? WHERE id = ?", (now, existing[0]))
    else:
        # Nếu chưa tồn tại -> thêm mới
        c.execute("""
            INSERT INTO indicators (ioc_value, ioc_type, source, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?)
        """, (ioc_value, ioc_type, source, now, now))
    
    if should_close:
        conn.commit()
        conn.close()
    
    return True

def add_iocs_batch(iocs_list):
    """
    Ghi nhiều IOC vào DB cùng lúc (batch insert/update) để tối ưu hiệu năng.
    Nhận vào list các dict có keys: ioc_value, ioc_type, source.
    Trả về số lượng IOC đã được ghi thành công.
    """
    if not iocs_list:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    # Tối ưu cho batch insert
    c = conn.cursor()
    try:
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA synchronous=NORMAL;")
        c.execute("PRAGMA cache_size=-64000;")  # 64MB cache
    except Exception:
        pass
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    written = 0
    
    try:
        # Lấy tất cả IOC cần kiểm tra trong một query duy nhất
        # Tạo dict để map (ioc_value, ioc_type) -> id nếu tồn tại
        existing_map = {}
        unique_keys = set()
        for ioc in iocs_list:
            ioc_value = ioc.get("ioc_value")
            ioc_type = ioc.get("ioc_type")
            if ioc_value and ioc_type:
                key = (ioc_value, ioc_type)
                unique_keys.add(key)
                existing_map[key] = None
        
        # Batch SELECT để kiểm tra IOC đã tồn tại chưa
        # SQLite không hỗ trợ tuple comparison, dùng OR với nhiều điều kiện
        # Tuy nhiên, SQLite có giới hạn expression tree depth = 1000, nên phải chia nhỏ batch
        # Chia thành các chunk nhỏ hơn để tránh lỗi "Expression tree is too large"
        if unique_keys:
            # Chia unique_keys thành các chunk nhỏ (500 items mỗi chunk để an toàn)
            chunk_size = 500
            unique_keys_list = list(unique_keys)
            
            for i in range(0, len(unique_keys_list), chunk_size):
                chunk = unique_keys_list[i:i + chunk_size]
                conditions = []
                values = []
                for key in chunk:
                    conditions.append("(ioc_value = ? AND ioc_type = ?)")
                    values.extend(key)
                
                query = "SELECT id, ioc_value, ioc_type FROM indicators WHERE " + " OR ".join(conditions)
                c.execute(query, values)
                for row in c.fetchall():
                    existing_map[(row[1], row[2])] = row[0]
        
        # Phân loại IOC thành insert và update
        to_insert = []
        to_update = []
        
        for ioc in iocs_list:
            ioc_value = ioc.get("ioc_value")
            ioc_type = ioc.get("ioc_type")
            source = ioc.get("source")
            
            if not ioc_value or not ioc_type or not source:
                continue
            
            key = (ioc_value, ioc_type)
            existing_id = existing_map.get(key)
            
            if existing_id:
                to_update.append((now, existing_id))
            else:
                to_insert.append((ioc_value, ioc_type, source, now, now))
        
        # Batch UPDATE
        if to_update:
            c.executemany(
                "UPDATE indicators SET last_seen = ? WHERE id = ?",
                to_update
            )
            written += len(to_update)
        
        # Batch INSERT
        if to_insert:
            c.executemany(
                "INSERT INTO indicators (ioc_value, ioc_type, source, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)",
                to_insert
            )
            written += len(to_insert)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    return written

def filter_iocs(
    ioc_value=None,
    ioc_type=None,
    source=None,
    first_from=None,
    first_to=None,
    last_from=None,
    last_to=None
):
    """
    Lọc IoC theo các thuộc tính cho trước.

    Các tham số:
        - ioc_value, ioc_type, source: giá trị chuỗi hoặc None
        - Không cung cấp tham số nào → lấy tất cả
        - Nếu only 'from' có giá trị → lấy từ ngày đó trở đi
        - Nếu only 'to' có giá trị → lấy đến ngày đó trở về trước
        - Nếu cả 'from' và 'to' có → lấy trong khoảng
        - Nếu 'from' == 'to' → lấy đúng ngày đó
    """

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = "SELECT * FROM indicators WHERE 1=1"
    params = []

    # Lọc theo ioc_value
    if ioc_value not in (None, 0, ""):
        query += " AND ioc_value = ?"
        params.append(ioc_value)

    # Lọc theo ioc_type
    if ioc_type not in (None, 0, ""):
        query += " AND ioc_type = ?"
        params.append(ioc_type)

    # Lọc theo source
    if source not in (None, 0, ""):
        query += " AND source = ?"
        params.append(source)

    if first_from and first_to:
        if first_from == first_to:
            query += " AND first_seen = ?"
            params.append(first_from)
        else:
            query += " AND first_seen BETWEEN ? AND ?"
            params.extend([first_from, first_to])
    elif first_from and not first_to:
        query += " AND first_seen >= ?"
        params.append(first_from)
    elif first_to and not first_from:
        query += " AND first_seen <= ?"
        params.append(first_to)

    # --- Lọc theo khoảng last_seen ---
    if last_from and last_to:
        if last_from == last_to:
            query += " AND last_seen = ?"
            params.append(last_from)
        else:
            query += " AND last_seen BETWEEN ? AND ?"
            params.extend([last_from, last_to])
    elif last_from and not last_to:
        query += " AND last_seen >= ?"
        params.append(last_from)
    elif last_to and not last_from:
        query += " AND last_seen <= ?"
        params.append(last_to)

    query += " ORDER BY last_seen DESC"

    c.execute(query, params)
    results = c.fetchall()
    conn.close()
    return results

def delete_iocs(
    ioc_value=None,
    ioc_type=None,
    source=None,
    first_from=None,
    first_to=None,
    last_from=None,
    last_to=None
):
    """
    Xóa IoC theo các thuộc tính cho trước.

    Tham số:
        - ioc_value, ioc_type, source: giá trị chuỗi hoặc None
        - Không cung cấp tham số nào → xóa tất cả
        - Nếu only 'from' có giá trị → lấy từ ngày đó trở đi
        - Nếu only 'to' có giá trị → lấy đến ngày đó trở về trước
        - Nếu cả 'from' và 'to' có → lấy trong khoảng
        - Nếu 'from' == 'to' → lấy đúng ngày đó
    """

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = "DELETE FROM indicators WHERE 1=1"
    params = []

    # --- Theo IoC value ---
    if ioc_value not in (None, 0, ""):
        query += " AND ioc_value = ?"
        params.append(ioc_value)

    # --- Theo IoC type ---
    if ioc_type not in (None, 0, ""):
        query += " AND ioc_type = ?"
        params.append(ioc_type)

    # --- Theo nguồn ---
    if source not in (None, 0, ""):
        query += " AND source = ?"
        params.append(source)

    # --- Khoảng thời gian first_seen ---
    if first_from and first_to:
        if first_from == first_to:
            query += " AND first_seen = ?"
            params.append(first_from)
        else:
            query += " AND first_seen BETWEEN ? AND ?"
            params.extend([first_from, first_to])
    elif first_from and not first_to:
        query += " AND first_seen >= ?"
        params.append(first_from)
    elif first_to and not first_from:
        query += " AND first_seen <= ?"
        params.append(first_to)

    # --- Khoảng thời gian last_seen ---
    if last_from and last_to:
        if last_from == last_to:
            query += " AND last_seen = ?"
            params.append(last_from)
        else:
            query += " AND last_seen BETWEEN ? AND ?"
            params.extend([last_from, last_to])
    elif last_from and not last_to:
        query += " AND last_seen >= ?"
        params.append(last_from)
    elif last_to and not last_from:
        query += " AND last_seen <= ?"
        params.append(last_to)

    # --- Ràng buộc logic ---
    if (first_from or first_to) and (last_from or last_to):
        query += " AND last_seen >= first_seen"

    # --- Thực thi ---
    c.execute(query, params)
    affected = c.rowcount
    conn.commit()
    conn.close()

    return affected  # Trả về số hàng đã bị xóa

if __name__ == "__main__":
    create_table()