# ThreatFeed Aggregator

Hệ thống thu thập và tổng hợp các Indicators of Compromise (IoC) từ nhiều nguồn threat intelligence khác nhau.

## Cấu trúc dự án

```
ThreatFeedAggregator
├─ analyze.py
├─ config
│  └─ config.yaml						
├─ core
│  ├─ aggregator.py
│  ├─ checkpoint.py
│  ├─ db.py
│  ├─ enricher.py
│  ├─ exporter.py
│  ├─ ioc_normalizer.py
│  ├─ pipeline.py
│  ├─ queue.py
│  └─ standardizer.py
├─ data
│  └─ database
├─ feeds
│  ├─ downloader.py
│  ├─ Fetch.py
│  └─ parser.py
├─ main.py
├─ models
│  ├─ feed_config.py
│  └─ ioc.py
├─ readme.md
├─ test.py
└─ utils
   ├─ config.py
   ├─ config_loader.py
   ├─ logger_util.py
   └─ scheduler.py
```

## Mô tả các thành phần

### Feeds Module (`feeds/`)
- `abusech_feed.py`: Thu thập dữ liệu từ Abuse.ch  
- `alienvault_feed.py`: Thu thập dữ liệu từ AlienVault OTX  
- Các module khác cho từng nguồn threat intelligence  
- `downloader.py` + `Fetch.py`: Quản lý tải feed  
- `parser.py`: Phân tích và chuẩn hóa dữ liệu feed thô  

### Core Module (`core/`)
- `aggregator.py`: Thu thập dữ liệu từ nhiều feed và loại bỏ trùng lặp  
- `ioc_normalizer.py` / `standardizer.py`: Chuẩn hóa IoC về định dạng chung  
- `db.py`: Hàm thao tác cơ sở dữ liệu (SQLite), lưu batch IoC  
- `queue.py`: File-backed queue cho producer/consumer  
- `exporter.py`: Xuất dữ liệu ra JSON/CSV  
- `pipeline.py`: Điều phối toàn bộ pipeline (enqueue, drain, checkpoint)  
- `checkpoint.py`: Quản lý checkpoint, hỗ trợ resume/interrupt  
- `enricher.py`: Bổ sung thông tin bổ sung cho IoC  

### Utils Module (`utils/`)
- `logger_util.py`: Cấu hình logging  
- `config_loader.py`: Đọc và xử lý file YAML (`feeds.yaml`, `settings.yaml`)  
- `scheduler.py`: Chạy các tác vụ theo lịch định kỳ  

### Configuration (`config/`)
- `feeds.yaml`: Danh sách nguồn feed, URL, tham số API  
- `settings.yaml`: Cấu hình chung (log path, output format, TTL, batch size...)  

### Data Storage (`data/`)
- `raw/`: Lưu dữ liệu feed thô  
- `processed/`: Dữ liệu đã chuẩn hóa và loại trùng  
- `database/`: SQLite DB lưu IoC  

---

## Cài đặt

```bash
pip install -r requirements.txt
```

## Sử dụng

```bash
python main.py
```

## Tính năng chính

- Thu thập IoC từ nhiều nguồn threat intelligence
- Chuẩn hóa dữ liệu về định dạng chung
- Loại bỏ các IoC trùng lặp
- Xuất dữ liệu ra nhiều định dạng (JSON, CSV)
- Hệ thống logging chi tiết

- Chạy tự động theo lịch trình

