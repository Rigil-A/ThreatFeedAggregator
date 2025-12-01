import gzip
from io import BytesIO, StringIO
from bs4 import BeautifulSoup
import requests
import json
import os

import csv
from datetime import datetime

# ======================================================================
# BƯỚC 1: DÁN CÁC API KEY CỦA BẠN TRỰC TIẾP VÀO ĐÂY
# ======================================================================
OTX_KEY = "a61fbc90f2d4e57c1761f3e6e5c35047d7935fdbfd5e6c8d4fe18f302f8e1030"
# ======================================================================

def fetch_abusech_to_json():
    """
    Lấy dữ liệu từ các nguồn của Abuse.ch và lưu vào một file JSON.
    """
    # Định nghĩa các nguồn feed từ abuse.ch
    feeds = {
        'URLhaus': 'https://urlhaus.abuse.ch/downloads/csv_recent/',
        'SSL Blacklist': 'https://sslbl.abuse.ch/blacklist/sslipblacklist.csv'
    }

    all_indicators = []
    print("🚀 Bắt đầu lấy dữ liệu từ Abuse.ch...")

    for name, url in feeds.items():
        try:
            print(f"\n📥 Đang tải xuống từ nguồn: {name}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = '\n'

            content = "\n".join([line for line in response.text.splitlines() if not line.strip().startswith('#')])
            if not content.strip(): 
                print(f"⚠️ Nguồn {name} không có dữ liệu sau khi lọc. Bỏ qua.")
                continue # Chuyển sang nguồn feed tiếp theo trong vòng lặp

            string_io_file = StringIO(content)
            reader = csv.reader(string_io_file)
            
            count = 0
            if name == 'URLhaus':
                for row in reader:
                    if len(row) >= 7:
                        all_indicators.append({
                            'source': 'Abuse.ch - URLhaus',
                            'first_seen': row[1],
                            'indicator_type': 'url',
                            'indicator': row[2],
                            'status': row[3],
                            'threat': row[5],
                            'tags':row[6]
                        })
                        count += 1
            
            elif name == 'SSL Blacklist':
                try:
                    next(reader) # Bỏ qua dòng tiêu đề
                    for row in reader:
                        if len(row) >= 2:
                            all_indicators.append({
                                'source': 'Abuse.ch - SSL Blacklist',
                                'first_seen': row[0],
                                'indicator_type': 'ipv4',
                                'indicator': row[1],
                                'status': f'Port: {row[2]}',
                                'threat': 'Malicious SSL Certificate',
                                'tags': 'sslipblacklist'
                            })
                            count += 1
                    
                except StopIteration:
                    print(f"⚠️ Nguồn {name} không có dữ liệu để xử lý (có thể file rỗng). Bỏ qua.")
                    continue # Bỏ qua và tiếp tục vòng lặp
            print(f"✅ Đã xử lý {count} chỉ số từ {name}.")
        except requests.exceptions.RequestException as e:
            print(f"❌ Lỗi khi tải {name}: {e}")

            

    if not all_indicators:
        print("\nKhông lấy được dữ liệu nào. Kết thúc.")
        return

    # === THAY ĐỔI CHÍNH Ở ĐÂY ===
    # Đóng gói tất cả dữ liệu vào một đối tượng dictionary duy nhất
    final_data = {
        "source_group": "Abuse.ch",
        "fetch_time": datetime.now().isoformat(),
        "indicator_count": len(all_indicators),
        "indicators": all_indicators
    }

    output_filename = "data/abuse_ch_indicators.json"
    output_dir = os.path.dirname(output_filename)
    if output_filename:
        os.makedirs(output_dir, exist_ok=True)
    try:
        # Ghi đối tượng dictionary này vào file JSON
        with open(output_filename, 'w', encoding='utf-8') as f:
            # indent=4 giúp file JSON có định dạng đẹp, dễ đọc
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        
        print(f"\n🏁 Hoàn thành! Đã lưu tổng cộng {len(all_indicators)} chỉ số vào file: {output_filename}")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file JSON: {e}")

def fetch_circl_to_json():
    # Hàm này thực hiện toàn bộ quá trình lấy dữ liệu từ CIRCL MISP feeds:
    # 1. Lấy danh sách link các file feed.
    # 2. Tải và xử lý từng file.
    # 3. Lưu tất cả các chỉ số (indicators) thu được vào một file JSON duy nhất.

    base_url = "https://www.circl.lu/doc/misp/feed-osint/"
    all_indicators = []

    # Giới hạn số file tải về để chạy demo nhanh hơn. 
    # Đặt giá trị này là None để tải tất cả các file.
    FILE_LIMIT = 20 

    print("🚀 Bắt đầu quá trình lấy dữ liệu từ CIRCL MISP OSINT Feed...")

    try:
        print(f"🔍 Đang tìm danh sách file tại trang chủ: {base_url}...")

        resp_main = requests.get(base_url, timeout=10)
        resp_main.raise_for_status()  # Báo lỗi nếu không truy cập được trang
        
        soup = BeautifulSoup(resp_main.text, 'lxml') # làm sạch các thẻ html

        #Lấy ra danh sách các file .json và json.gz
        links = [
            f"{base_url}{a['href']}" for a in soup.find_all('a', href=True) 
            if a['href'].endswith(('.json', '.json.gz'))
        ]
        
        #nếu không có file nào 
        if not links:
            print("❌ Không tìm thấy link file feed nào. Dừng lại.")
            return

        #Kiểm tra nếu không có giới hạn thì tải toàn bộ
        links_to_process = links[:FILE_LIMIT] if FILE_LIMIT is not None else links
        print(f"🔗 Đã tìm thấy {len(links)} file. Sẽ xử lý {len(links_to_process)} file (do giới hạn FILE_LIMIT={FILE_LIMIT}).")

        #idx là biến đếm số thứ tự các file đang được xử lí
        for idx, url in enumerate(links_to_process):
            filename = url.split('/')[-1] #trích xuất các tên file json
            try:
                print(f"📥 [{idx + 1}/{len(links_to_process)}] Đang tải và xử lý file: {filename}")
                
                # Gửi request đến url tương ứng với tên file
                resp_file = requests.get(url, timeout=45)
                resp_file.raise_for_status()

                # Giải nén nếu là file .gz
                if url.endswith(".gz"):
                    # BytesIO đọc content của response như một file trong bộ nhớ
                    with gzip.open(BytesIO(resp_file.content), 'rt', encoding='utf-8') as gz:
                        data = json.load(gz)
                else:
                    data = json.loads(resp_file.text)
                
                # Trích xuất thông tin từ cấu trúc MISP Event
                event = data.get("Event", {})
                event_info = event.get("info", "N/A")
                tags = "; ".join([tag.get("name", "") for tag in event.get("Tag", [])])

                # Lấy các "Attribute" - đây chính là thông tin của các indicators
                for attr in event.get("Attribute", []):
                    #làm sạch theo format có sẵn
                    all_indicators.append({
                        'source': 'CIRCL MISP OSINT',
                        'source_file': filename,
                        'first_seen': datetime.fromtimestamp(int(attr.get("timestamp"))).isoformat() if attr.get("timestamp") else None,
                        'indicator_type': attr.get("type"),
                        'indicator': attr.get("value"),
                        'category': attr.get("category"),
                        'threat_event': event_info,
                        'tags': tags
                    })

            except Exception as e:
                print(f"    └─ ❌ Lỗi khi xử lý file {filename}: {e}")

    except requests.RequestException as e:
        print(f"❌ Lỗi nghiêm trọng khi truy cập CIRCL: {e}")
        return # Dừng hàm nếu không thể kết nối

    if not all_indicators:
        print("\n🏁 Không trích xuất được chỉ số nào. Kết thúc.")
        return

    # Nội dung của file sau khi đã đc làm sạch
    final_data = {
        "source_group": "CIRCL MISP OSINT",
        "fetch_time": datetime.now().isoformat(),
        "files_processed": len(links_to_process),
        "indicator_count": len(all_indicators),
        "indicators": all_indicators
    }
    
    # Đặt tên file (có thể thay đổi tùy ý)
    output_filename = "data/circl_indicators.json"
    output_dir = os.path.dirname(output_filename)
    if output_filename:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n🏁 Hoàn thành! Đã lưu tổng cộng {len(all_indicators)} chỉ số vào file: {output_filename}")


def fetch_otx_to_json():

    #Lấy các chỉ số (indicators) từ OTX và lưu vào file JSON.

    if not OTX_KEY or "YOUR_OTX_API_KEY_HERE" in OTX_KEY:
        print("⚠️  OTX_API_KEY chưa được thiết lập. Bỏ qua...")
        return

    url = "https://otx.alienvault.com/api/v1/pulses/subscribed"
    headers = {"X-OTX-API-KEY": OTX_KEY} # header dùng để gửi request đến url
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()

        iocs = []
        #Làm sạch dữ liệu
        for pulse in data.get("results", []):
            for indicator in pulse.get("indicators", []):
                iocs.append({
                    "indicator": indicator.get("indicator"),
                    "type": indicator.get("type"),
                    "created": indicator.get("created"),
                    "pulse_name": pulse.get("name")
                })
        # Dữ liệu đầu ra
        output_data = {
            "source": "AlienVault OTX Subscribed Pulses",
            "fetch_time": datetime.now().isoformat(),
            "count": len(iocs),
            "indicators": iocs
        }
        output_filename = "data/otx_indicators.json"
        output_dir = os.path.dirname(output_filename)
        if output_filename:
            os.makedirs(output_dir  , exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        print(f"✅ Đã lưu thành công {len(iocs)} chỉ số OTX vào file: {output_filename}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi gọi API OTX: {e}")

    return output_data
        