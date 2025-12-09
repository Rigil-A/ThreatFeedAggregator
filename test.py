from core.exporter import IOCExporter

if __name__ == '__main__':
    exporter = IOCExporter()  # tạo instance
    IoCs = exporter.export_from_db(fmt='json', db_path="data/database/ioc_database.db")
    print(IoCs)