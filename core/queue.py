import os, json,time

import msvcrt


class File_queue:
    def __init__(self, queue_path):
        self.queue_path = queue_path #  Đường dẫn đến file chứa queue vd: "data/queues/<name>.queue"
        self.lock_path = queue_path + '.lock' # Tạo file khóa trên cùng đường dẫn đến hàng đợi, để tránh nhiều tiến trình cùng truy cập vào 1 file
        self._lock_file = None   # Khởi tạo một biến để giữ đối tượng file khóa, ban đầu là None (chưa có gì)

        #Tạo thư mục chứa file queue nếu chưa tồn tại
        queue_dir = os.path.dirname(queue_path)
        if not os.path.exists(queue_dir):
            os.makedirs(queue_dir)

    #Xử lý quá trình khóa file
    def _acquire_lock(self): 
        #Chiếm giữ file lock để đảm bảo chỉ có 1 tiến trình được truy cập.
        try:
            self._lock_file = open(self.lock_path, 'w')
        except Exception as e:
            print(f"Can't not open {self.lock_path}: {e}")  
            return False
        
        #Khóa file này
        try:
            #fileno:  Lấy "số hiệu" của file đang mở
            #LK_NBLCK: Chế độ khóa không chờ (Non-Blocking Lock). Nếu file đã bị khóa, nó sẽ báo lỗi ngay lập tức.
            # 1: Khóa 1 byte đầu tiên của file.
            msvcrt.locking(self._lock_file.fileno(),msvcrt.LK_NBLCK, 1)
            return True
        except IOError:
            return False
        
    #Giải phóng file khóa    
    def _release_lock(self):
        # Kiểm tra xem biến _lock_file có đang giữ một file đã mở hay không
        if self._lock_file:
            # Di chuyển con trỏ về đầu file (vị trí byte 0)
            self._lock_file.seek(0)
            #LK_UNLCK: chế độ mở khóa
            #1: mở khóa byte đầu
            msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK,1)

            
            self._lock_file.close()#đóng file
            self._lock_file = None #Báo lại không còn file nào bị khóa

            #xóa file lock (optional)
            if os.path.exists(self.lock_path):
                try:
                    os.remove(self.lock_path)
                except OSError:
                    pass
    
    #Kiểm tra file đã được khóa chưa
    def _wait_for_lock(self):
        while not self._acquire_lock():
            time.sleep(0.05)

    # Hàm để thêm một item vào cuối hàng đợi
    def push(self, item):
        self._wait_for_lock() # chờ đến khi file được khóa
        try:
            #a: cho phép ghi vào cuối file
            with open(self.queue_path, 'a') as f:
                #chuyên đổi item thành dạng json rồi ghi vào file
                f.write(json.dumps(item)+'\n')
        #đảm bảo có lỗi vẫn có thể giải phóng lock
        finally:
            self._release_lock()

    # Hàm để lấy ra và xóa item đầu tiên khỏi hàng đợi
    def pop(self):
        # Nếu file không tồn tại hoặc kích thước bằng 0, trả về None ngay lập tức
        if not os.path.exists(self.queue_path) or os.path.getsize(self.queue_path) == 0:
            
            return None
        
        
        self._acquire_lock() #Chờ file khóa
        item = None 
        try:
            #"r+" có thể đọc và ghi
            with open(self.queue_path, 'r+') as f:
                lines = f.readlines()   # Đọc tất cả các dòng trong file vào một danh sách (list)
                #nếu không có dòng nào trả về None
                if not lines:
                    return None
                
                first_line = lines[0].strip() # Lấy dòng đầu tiên và dùng .strip() để xóa các khoảng trắng hoặc ký tự xuống dòng thừa
                item = json.loads(first_line) # Chuyển chuỗi JSON lấy được trở lại thành đối tượng Python
                f.seek(0) # Di chuyển con trỏ về lại đầu file (vị trí byte 0) để chuẩn bị ghi đè
                f.writelines(lines[1:]) #Ghi lại tất cả các dòng TRỪ DÒNG ĐẦU TIÊN
                f.truncate() #Cắt bỏ phần nội dung còn thừa ở cuối file (nếu file mới ngắn hơn file cũ)
        except (IOError, json.JSONDecodeError) as e:
            print(f"[ERROR] Could not pop from {self.queue_path}: {e}")
            return None
        #Luôn đảm bảo giải phóng lock sau khi hoàn tất
        finally:
            self._release_lock()
        return item
    #Hàm để kiểm tra kích thước (số lượng item) của hàng đợi
    def size(self):
        self._wait_for_lock() #Phải chờ lock để có kết quả chính xác.
        count = 0
        try:
            # Mở file ở chế độ chỉ đọc 'r'
            with open(self.queue_path, 'r') as f:
                # Đếm số lượng dòng trong file, đây chính là số item trong hàng đợi
                count = len(f.readlines())
        except FileNotFoundError:
            # Nếu file không tồn tại, coi như hàng đợi rỗng, kích thước là 0
            count = 0
        finally:
            self._release_lock()
        return count