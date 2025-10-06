# ThreatFeed Aggregator

Hệ thống thu thập và tổng hợp các Indicators of Compromise (IoC) từ nhiều nguồn threat intelligence khác nhau.

## Cấu trúc dự án

```
ThreatFeed-Aggregator/
│
├── feeds/                      # Các module fetch dữ liệu từ nguồn
│   ├── abusech_feed.py
│   ├── alienvault_feed.py
│   └── ...
│
├── core/                       # Thành phần xử lý lõi
│   ├── aggregator.py          # Hàm chính thu thập từ nhiều nguồn, loại trùng
│   ├── normalizer.py          # Chuẩn hóa IoC về định dạng chung
│   ├── db.py                  # Các hàm thao tác với database
│   ├── queue.py               # Tổ chức hàng đợi xử lý
│   └── exporter.py            # Xuất dữ liệu ra JSON/CSV
│
├── utils/                     # Tiện ích chung
│   ├── logger_util.py         # Cấu hình ghi log
│   ├── config_loader.py       # Đọc file config.yaml
│   └── scheduler.py           # Chạy định kỳ (cron/schedule library)
│
├── config/                    # File cấu hình
│   ├── feeds.yaml             # Danh sách nguồn feed, URL, tham số API
│   └── settings.yaml          # Cấu hình chung: log path, output format, TTL,...
│
├── data/                      # Dữ liệu IoC đã thu thập
│   ├── raw/                   # Dữ liệu thô từ từng feed
│   └── processed/             # Dữ liệu đã chuẩn hóa + loại trùng
│
├── logs/                      # File log
│   └── aggregator.log
│
├── output/                    # Dữ liệu xuất từ exporter
│   ├── ioc-latest.json
│   ├── ioc-latest.csv
│   └── summary.txt
│
├── main.py                    # Entry point chính của chương trình
├── requirements.txt           # Danh sách thư viện cần cài
├── .gitignore
└── README.md
```

## Mô tả các thành phần

### Feeds Module (`feeds/`)
- **abusech_feed.py**: Thu thập dữ liệu từ Abuse.ch
- **alienvault_feed.py**: Thu thập dữ liệu từ AlienVault OTX
- Các module khác cho từng nguồn threat intelligence

### Core Module (`core/`)
- **aggregator.py**: Hàm chính thu thập từ nhiều nguồn và loại bỏ trùng lặp
- **normalizer.py**: Chuẩn hóa IoC về định dạng chung
- **db.py**: Các hàm thao tác với cơ sở dữ liệu
- **queue.py**: Tổ chức hàng đợi xử lý
- **exporter.py**: Xuất dữ liệu ra các định dạng JSON/CSV

### Utils Module (`utils/`)
- **logger_util.py**: Cấu hình hệ thống ghi log
- **config_loader.py**: Đọc và xử lý file cấu hình YAML
- **scheduler.py**: Chạy các tác vụ định kỳ

### Configuration (`config/`)
- **feeds.yaml**: Danh sách nguồn feed, URL, tham số API
- **settings.yaml**: Cấu hình chung như đường dẫn log, định dạng output, TTL

### Data Storage (`data/`)
- **raw/**: Dữ liệu thô từ từng nguồn feed
- **processed/**: Dữ liệu đã được chuẩn hóa và loại bỏ trùng lặp

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