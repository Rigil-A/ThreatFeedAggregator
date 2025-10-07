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
    conn.commit()
    conn.close()

def add_ioc(ioc_value, ioc_type, source):
    conn = sqlite3.connect(DB_PATH)
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
    
    conn.commit()
    conn.close()

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