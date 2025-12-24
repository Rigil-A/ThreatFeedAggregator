# ThreatFeed Aggregator

**ThreatFeedAggregator** là một công cụ mạnh mẽ được thiết kế để thu thập, tổng hợp, chuẩn hóa và loại bỏ trùng lặp các nguồn Threat Intelligence từ nhiều feed công khai khác nhau. Trên Internet có rất nhiều dữ liệu về các mối đe dọa, bao gồm danh sách IP độc hại, domain C&C, malware hash, và các nguồn feed JSON/TXT từ các tổ chức bảo mật. ThreatFeedAggregator giúp bạn tự động hóa quá trình này, đưa tất cả dữ liệu về một định dạng chung, dễ sử dụng và dễ phân tích.

### Tính năng chính
Công cụ hỗ trợ:

- **Thu thập đa nguồn**: Dữ liệu từ ít nhất 5 nguồn Threat Intelligence công khai, có thể mở rộng thêm các nguồn mới bằng cách cấu hình trong file YAML.
- **Loại trùng & toàn vẹn**: Tổng hợp và loại bỏ các IoC trùng lặp trước khi lưu vào cơ sở dữ liệu SQLite, đảm bảo dữ liệu sạch và duy nhất.
- **Chuẩn hóa**: Chuẩn hóa các IoC về định dạng chung, bao gồm IP, domain, URL, hash, giúp việc phân tích và chia sẻ trở nên thuận tiện.
- **Xuất linh hoạt**: Xuất dữ liệu ra các định dạng phổ biến như file text (mỗi dòng một IoC) hoặc JSON, sẵn sàng sử dụng cho các hệ thống bảo mật khác.
- **Chạy tự động**: Hỗ trợ chạy theo lịch trình định kỳ với scheduler, kết hợp checkpoint và resume để đảm bảo pipeline không bị gián đoạn.
- **Logging & Debug**: Logging chi tiết, giúp theo dõi trạng thái thu thập và debug dễ dàng.

### Công nghệ sử dụng

ThreatFeedAggregator được phát triển bằng **Python**, sử dụng thư viện `requests` để tải dữ liệu và `sqlite3` để lưu trữ tạm thời. Thiết kế cũng hỗ trợ mở rộng cho các ngôn ngữ khác như Go để xử lý các tác vụ liên quan đến mạng và concurrency.

Sản phẩm đi kèm bao gồm: mã nguồn công cụ, file cấu hình mẫu để thêm các nguồn feed, và hướng dẫn sử dụng đầy đủ.

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





