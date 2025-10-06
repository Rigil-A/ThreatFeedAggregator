ThreatFeed-Aggregator/
│
├── feeds/                      # Các module fetch
│   ├── abusech_feed.py
│   ├── alienvault_feed.py
│   ├── ...
│   └── ...
│
├── core/                       # Thành phần xử lý lõi
│   ├── aggregator.py           # Hàm chính thu thập từ nhiều nguồn, loại trùng
│   ├── normalizer.py           # Chuẩn hóa IoC về định dạng chung
│   ├── db.py                   # Các hàm thao tác với database
│   ├── queue.py                # Tổ chức hàng đợi xử lý
│   └── exporter.py             # Xuất dữ liệu ra JSON/CSV
│
├── utils/                      # Tiện ích chung
│   ├── logger_util.py          # Cấu hình ghi log
│   ├── config_loader.py        # Đọc file config.yaml
│   └── scheduler.py            # Chạy định kỳ (cron/schedule library)
│
├── config/                     # File cấu hình
│   ├── feeds.yaml              # Danh sách nguồn feed, URL, tham số API
│   └── settings.yaml           # Cấu hình chung: log path, output format, TTL,...
│
├── data/                       # Dữ liệu IoC đã thu thập
│   ├── raw/                    # Dữ liệu thô từ từng feed
│   └── processed/              # Dữ liệu đã chuẩn hóa + loại trùng
│
├── logs/                       # File log
│   └── aggregator.log
│
├── output/                     # Dữ liệu xuất từ exporter
│   ├── ioc-latest.json
│   ├── ioc-latest.csv
│   └── summary.txt
│
├── main.py                     # Entry point chính của chương trình
│
├── requirements.txt            # Danh sách thư viện cần cài (cập nhật thường xuyên)
├── .gitignore
└── README.md                   
