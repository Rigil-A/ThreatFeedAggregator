# ThreatFeed Aggregator

Hệ thống thu thập và tổng hợp các Indicators of Compromise (IoC) từ nhiều nguồn threat intelligence khác nhau.

## Cấu trúc dự án

```
ThreatFeed-Aggregator/
│
├── feeds/                      # Các module fetch dữ liệu từ nguồn (parsers)
│   ├── abusech_feed.py
│   ├── alienvault_feed.py
│   └── ...
│
├── core/                      # Thành phần xử lý lõi
│   ├── aggregator.py          # Hàm chính thu thập từ nhiều nguồn, loại trùng
│   ├── normalizer.py          # Chuẩn hóa IoC về định dạng chung
│   ├── db.py                  # Các hàm thao tác với database
│   ├── queue.py               # Tổ chức hàng đợi xử lý
│   └── exporter.py            # Xuất dữ liệu ra JSON/CSV
│
├── utils/                     # Tiện ích chung
│   ├── logger_util.py         # Cấu hình ghi log
│   ├── config_loader.py       # Đọc file config.yaml
│   └── scheduler.py           # Chạy định kỳ (cron/schedule library) (luôn mở terminal)
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
├── models/                    # Mappings hoặc model artifacts
├── ttp_mapping/               # (optional) ttp id -> name mappings
├── scripts/                   # helper scripts (e.g. validate_environment.ps1)
│
├── analyze.py                 # Phân tích queue + biểu đồ
├── extract_ioc_from_pdf.py    # Trích IOC từ PDF và in ra console
├── extract_ioc_to_json.py     # Trích IOC từ PDF và lưu JSON
├── extract_ttp.py             # TTP extraction helper (yêu cầu ML deps)
├── setup_scheduler.ps1        # PowerShell helper để tạo Task Scheduler
├── main.py                    # Entry point chính của chương trình
├── requirements.txt           # Danh sách thư viện cần cài
├── .gitignore
└── README.md
```

## Mô tả các thành phần

### Feeds Module (`feeds/`)
- **Fetch.py**: Quản lý việc tải feeds và phân phối dữ liệu tới các parser.
- **downloader.py**: Tiện ích tải HTTP (retry, timeout) cho các feed.
- **parser.py**: Parser chung hỗ trợ CSV/JSON/freetext và regex phát hiện IOC.

### Core Module (`core/`)
- **aggregator.py**: Hàm chính thu thập từ nhiều nguồn và loại bỏ trùng lặp
- **pipeline.py**: Điều phối toàn bộ luồng xử lý và trả về thống kê.
- **ioc_normalizer.py**: Chuẩn hóa định dạng IOC.
- **db.py**: Các hàm thao tác với cơ sở dữ liệu
- **queue.py**: Tổ chức hàng đợi xử lý
- **exporter.py**: Xuất kết quả ra CSV/JSON trong `output/`.
- **enricher.py**: (Tùy chọn) tăng cường thông tin cho IOC.
- **checkpoint.py**: Lưu và phục hồi checkpoint xử lý.
- **standardizer.py**: Các hàm chuẩn hóa bổ sung.

### Utils Module (`utils/`)
- **logger_util.py**: Cấu hình hệ thống ghi log
- **config_loader.py**: Đọc và xử lý file cấu hình YAML
- **config.py**: Hằng số và cài đặt mặc định dự án.
- **scheduler.py**: Scheduler nội bộ, lưu PID vào `data/processed/scheduler.pid`.
- **service_manager.py**: Tiện ích hỗ trợ quản lý tiến trình/tác vụ nền.

### Configuration (`config/`)
- **config.yaml**: File cấu hình chính (feeds và các cài đặt chung).

### Data Storage (`data/`)
- **raw/**: Dữ liệu thô tải về từ các feed
- **processed/**: Dữ liệu đã xử lý/chuẩn hóa
  - **ioc.queue**: Hàng đợi IOC chờ xử lý (`data/processed/ioc.queue`)
  - **scheduler.pid**: PID của scheduler nội bộ nếu đang chạy (`data/processed/scheduler.pid`)
  - **database/**: Thư mục chứa file DB nhẹ (nếu có)

## Cài đặt

```bash
pip install -r requirements.txt
```

## Sử dụng

- Chạy tương tác (menu):

```bash
python main.py
```

- Chạy một lần (dùng cho automation / Task Scheduler):

```bash
python main.py --fetch-once
```

- Chạy scheduler nội bộ (chạy liên tục trong foreground):

```bash
python main.py --scheduler --work-hour <giờ> --work-minute <phút>
```

- Dừng scheduler nội bộ (khi đã có PID):

```bash
python main.py --stop-scheduler
```

Ghi chú:
- `--fetch-once` thích hợp để chạy từ Task Scheduler hoặc cron (chạy xong thì exit).
- `--scheduler` sẽ lưu PID vào `data/processed/scheduler.pid` và chạy vòng lặp mỗi ngày vào giờ chỉ định.
- Khi gặp vấn đề: xem `logs/aggregator.log` để biết pipeline có được khởi động và có lỗi gì không.

**Chạy `setup_scheduler.ps1` (Windows Task Scheduler helper)**

- Mở PowerShell dưới quyền Administrator và vào thư mục project:

```powershell
Set-Location E:\ThreatFeedAggregator
powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1
```

- Tạo task với thời gian tuỳ chỉnh:

```powershell
powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1 -Hour 2 -Minute 0
```

- Các lệnh quản lý task:

```powershell
# Kiểm tra trạng thái
powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1 -Action status

# Chạy ngay bây giờ
powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1 -Action run

# Xóa task
powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1 -Action delete
```

Ví dụ các script tiện ích khác:

```bash
python analyze.py                    # Phân tích data/processed/ioc.queue và xuất biểu đồ
python extract_ioc_from_pdf.py file.pdf   # Trích IOC từ PDF và in ra console
python extract_ioc_to_json.py file.pdf    # Trích IOC và lưu ra JSON
```

## Tính năng chính

- Thu thập IoC từ nhiều nguồn threat intelligence
- Chuẩn hóa dữ liệu về định dạng chung
- Loại bỏ các IoC trùng lặp
- Xuất dữ liệu ra nhiều định dạng (JSON, CSV)
- Hệ thống logging chi tiết
- Chạy tự động theo lịch trình