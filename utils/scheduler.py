"""
Scheduler module để tự động chạy ThreatIntelPipeline vào giờ hành chính mỗi sáng.
Sử dụng thư viện schedule để lập lịch.
"""
import schedule
import time
import os
import signal
from datetime import datetime
from core.pipeline import ThreatIntelPipeline
from utils.logger_util import setup_logging, get_logger

# Flag để kiểm soát việc dừng scheduler
_stop_scheduler = False

# Đường dẫn file lưu PID của scheduler
PID_FILE = "data/processed/scheduler.pid"


def run_pipeline():
    """
    Chạy pipeline và xử lý kết quả.
    Hàm này sẽ được gọi bởi scheduler.
    """
    logger = get_logger(__name__)
    logger.info("=" * 60)
    logger.info("Scheduled pipeline execution started at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)
    
    try:
        pipeline = ThreatIntelPipeline()
        # Khi chạy tự động, không hỏi người dùng, tự động resume nếu có queue
        feed_count, total_enqueued, total_written, all_iocs = pipeline.run(
            skip_enqueue_if_exists=True, 
            auto_resume=True
        )
        
        logger.info(
            "Scheduled pipeline completed: feeds=%d, enqueued=%d, written=%d, collected=%d",
            feed_count, total_enqueued, total_written, len(all_iocs) if all_iocs else 0
        )
        
        if all_iocs and len(all_iocs) > 0:
            logger.info("Successfully processed %d IOCs", len(all_iocs))
        else:
            logger.warning("No IOCs were collected in this run")
            
    except KeyboardInterrupt:
        logger.warning("Pipeline execution interrupted by user")
        raise
    except Exception as e:
        logger.error("Pipeline execution failed: %s", e, exc_info=True)
        # Không raise exception để scheduler có thể tiếp tục chạy vào lần sau


def _signal_handler(signum, frame):
    """Xử lý signal để dừng scheduler một cách lịch sự"""
    global _stop_scheduler
    logger = get_logger(__name__)
    logger.info("Received stop signal. Scheduler will stop after current operation...")
    _stop_scheduler = True


def stop_scheduler():
    """
    Dừng scheduler một cách lịch sự.
    Có thể gọi từ code hoặc từ signal handler.
    """
    global _stop_scheduler
    _stop_scheduler = True


def save_pid():
    """Lưu PID của process hiện tại vào file"""
    pid_dir = os.path.dirname(PID_FILE)
    if pid_dir and not os.path.exists(pid_dir):
        os.makedirs(pid_dir, exist_ok=True)
    
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger = get_logger(__name__)
        logger.warning("Could not save PID file: %s", e)


def remove_pid():
    """Xóa file PID"""
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except Exception:
            pass


def get_scheduler_pid():
    """Đọc PID của scheduler từ file"""
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
            return pid
    except (ValueError, IOError):
        return None


def stop_scheduler_process():
    """
    Dừng scheduler process đang chạy bằng cách gửi SIGTERM signal.
    Trả về True nếu thành công, False nếu không tìm thấy scheduler.
    """
    pid = get_scheduler_pid()
    if pid is None:
        return False
    
    try:
        # Kiểm tra xem process có còn tồn tại không
        os.kill(pid, 0)  # Signal 0 chỉ kiểm tra, không gửi signal thực sự
    except (OSError, ProcessLookupError):
        # Process không tồn tại, xóa file PID
        remove_pid()
        return False
    
    try:
        # Gửi SIGTERM để dừng scheduler một cách lịch sự
        os.kill(pid, signal.SIGTERM)
        return True
    except (OSError, ProcessLookupError):
        remove_pid()
        return False


def start_scheduler(work_hour: int = 8, work_minute: int = 0):
    """
    Khởi động scheduler để chạy pipeline tự động mỗi sáng vào giờ hành chính.
    
    Args:
        work_hour: Giờ hành chính (mặc định 8:00)
        work_minute: Phút (mặc định 0)
    """
    global _stop_scheduler
    _stop_scheduler = False
    
    logger = get_logger(__name__)
    
    # Kiểm tra xem scheduler đã chạy chưa
    existing_pid = get_scheduler_pid()
    if existing_pid:
        try:
            # Kiểm tra process có còn tồn tại không
            os.kill(existing_pid, 0)
            logger.warning("Scheduler is already running (PID: %d)", existing_pid)
            print(f"[WARNING] Scheduler is already running with PID {existing_pid}")
            print("[INFO] Use 'python main.py --stop-scheduler' to stop it first")
            return
        except (OSError, ProcessLookupError):
            # Process không tồn tại, xóa file PID cũ
            remove_pid()
    
    # Lưu PID của process hiện tại
    save_pid()
    
    # Đăng ký signal handler để xử lý Ctrl+C và SIGTERM
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    
    # Lập lịch chạy mỗi ngày vào giờ hành chính
    schedule_time = f"{work_hour:02d}:{work_minute:02d}"
    schedule.every().day.at(schedule_time).do(run_pipeline)
    
    logger.info("Scheduler started (PID: %d). Pipeline will run daily at %s", os.getpid(), schedule_time)
    logger.info("Press Ctrl+C or use 'python main.py --stop-scheduler' to stop")
    print("\n[INFO] Scheduler is running...")
    print(f"[INFO] PID: {os.getpid()}")
    print("[INFO] Press Ctrl+C or use 'python main.py --stop-scheduler' to stop")
    print(f"[INFO] Next run scheduled at {schedule_time}\n")
    
    # Chạy scheduler trong vòng lặp
    try:
        while not _stop_scheduler:
            schedule.run_pending()
            # Kiểm tra flag mỗi giây để phản hồi nhanh hơn
            for _ in range(60):
                if _stop_scheduler:
                    break
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user (KeyboardInterrupt)")
        _stop_scheduler = True
    except Exception as e:
        logger.error("Scheduler error: %s", e, exc_info=True)
    finally:
        # Dọn dẹp: xóa file PID và thông báo dừng
        remove_pid()
        logger.info("Scheduler stopped")
        print("\n[INFO] Scheduler has been stopped")


if __name__ == "__main__":
    # Khởi tạo logging
    setup_logging()
    logger = get_logger(__name__)
    
    # Có thể thay đổi giờ hành chính ở đây (mặc định 8:00)
    WORK_HOUR = 13
    WORK_MINUTE = 28
    
    logger.info("Starting Threat Intelligence Pipeline Scheduler")
    logger.info("Pipeline will run daily at %02d:%02d", WORK_HOUR, WORK_MINUTE)
    
    # Khởi động scheduler
    start_scheduler(work_hour=WORK_HOUR, work_minute=WORK_MINUTE)

