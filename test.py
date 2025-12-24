import os
from core import db

def remove_db():
    db_path = db.DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Đã xóa database: {db_path}")
    else:
        print(f"Không tìm thấy database: {db_path}")

def test_db_basic():
    db.create_tables()
    print("Đã tạo lại các bảng.")
    # Thêm fetch_history
    fetch_id = db.insert_fetch_history(total_src=3, total_ioc=10, new_ioc=5)
    print(f"Thêm fetch_history, fetch_id={fetch_id}")
    # Thêm một IoC
    result = db.add_ioc("1.2.3.4", "ip", fetch_id)
    print(f"Thêm IoC mới: {result}")
    # Thêm lại IoC (score tăng)
    result2 = db.add_ioc("1.2.3.4", "ip", fetch_id)
    print(f"Cập nhật IoC (score tăng): {result2}")
    # Batch insert
    iocs = [
        {"ioc_value": "abc.com", "ioc_type": "domain"},
        {"ioc_value": "abcd.com", "ioc_type": "domain"},
        {"ioc_value": "1.2.3.4", "ioc_type": "ip"},
    ]
    new_count = db.add_iocs_batch(iocs, fetch_id)
    print(f"Batch insert, số IoC mới: {new_count}")
    # Lọc IoC
    filtered = db.filter_iocs(ioc_type="domain")
    print(f"Lọc IoC domain: {filtered}")
    # Xóa IoC
    deleted = db.delete_iocs(ioc_value="abc.com", ioc_type="domain")
    print(f"Đã xóa IoC abc.com: {deleted}")
    # Lọc lại
    filtered2 = db.filter_iocs(ioc_type="domain")
    print(f"Lọc lại IoC domain: {filtered2}")

def main():
    remove_db()
    test_db_basic()

if __name__ == "__main__":
    main()
