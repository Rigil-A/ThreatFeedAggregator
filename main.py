from core.pipeline import ThreatIntelPipeline
from utils.logger_util import setup_logging, get_logger
from core.exporter import IOCExporter
import argparse
import csv
from datetime import datetime

# last in-memory IOCs & last export results (used by interactive menu)
_last_iocs = None
_last_export_results = None


def run_once():
    """
    Chạy pipeline một lần và xuất kết quả.
    """
    logger = get_logger(__name__)
    
    try:
        # ThreatIntelPipeline điều khiển toàn bộ luồng thực thi.
        pipeline = ThreatIntelPipeline()
        feed_count, total_enqueued, total_written, all_iocs = pipeline.run()

        # Phần còn lại của main giữ gần như logic cũ: in thống kê + xuất CSV + in vài IOC đầu
        if all_iocs is None:
            logger.error("pipeline.run() returned no IOC list")
            print("[ERROR] pipeline.run() returned no IOC list")
            exit(1)
        
        if len(all_iocs) == 0:
            logger.warning("Pipeline completed but no IOCs were collected")
            print("[WARNING] No IOCs collected from feeds")
            exit(0)

        print(f"[✓] Total IOCs: {len(all_iocs)}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use IOCExporter to export to multiple formats and keep last results in memory
        exporter = IOCExporter(output_dir="output")
        global _last_iocs, _last_export_results
        _last_iocs = all_iocs
        _last_export_results = exporter.export_all_formats(all_iocs, base_filename=f"iocs_{timestamp}")

        # Report exported paths per format
        for fmt, path in _last_export_results.items():
            print(f"[✓] Saved ({fmt}): {path}")

        # Print 10 first IOCs for quick inspection
        for ioc in all_iocs[:10]:
            print(ioc.to_dict())

        # Ghi log tóm tắt pipeline
        summary = (
            f"Feeds={feed_count}, "
            f"IOCs enqueued={total_enqueued}, "
            f"IOCs written DB={total_written}, "
            f"IOCs in_memory={len(all_iocs)}"
        )
        logger.info("Pipeline finished. %s", summary)
        
    except Exception as e:
        logger.error("Pipeline execution failed: %s", e, exc_info=True)
        print(f"[ERROR] Pipeline failed: {e}")
        exit(1)


def run_scheduler(work_hour: int = 8, work_minute: int = 0):
    """
    Chạy pipeline theo lịch tự động.
    
    Args:
        work_hour: Giờ hành chính (mặc định 8:00)
        work_minute: Phút (mặc định 0)
    """
    try:
        from utils.scheduler import start_scheduler
        logger = get_logger(__name__)
        logger.info("Starting scheduler mode. Pipeline will run daily at %02d:%02d", work_hour, work_minute)
        start_scheduler(work_hour=work_hour, work_minute=work_minute)
    except ImportError:
        print("[ERROR] Scheduler module requires 'schedule' library.")
        print("Please install it with: pip install schedule")
        exit(1)
    except Exception as e:
        logger = get_logger(__name__)
        logger.error("Scheduler failed: %s", e, exc_info=True)
        print(f"[ERROR] Scheduler failed: {e}")
        exit(1)


def stop_scheduler():
    """
    Dừng scheduler đang chạy.
    """
    try:
        from utils.scheduler import stop_scheduler_process, get_scheduler_pid
        logger = get_logger(__name__)
        
        pid = get_scheduler_pid()
        if pid is None:
            print("[INFO] Scheduler is not running")
            logger.info("No scheduler process found")
            return
        
        print(f"[INFO] Stopping scheduler (PID: {pid})...")
        logger.info("Attempting to stop scheduler (PID: %d)", pid)
        
        if stop_scheduler_process():
            print("[INFO] Scheduler stop signal sent successfully")
            print("[INFO] Scheduler will stop gracefully after current operation")
            logger.info("Scheduler stop signal sent successfully")
        else:
            print("[WARNING] Scheduler process not found or already stopped")
            logger.warning("Scheduler process not found")
    except ImportError:
        print("[ERROR] Scheduler module requires 'schedule' library.")
        print("Please install it with: pip install schedule")
        exit(1)
    except Exception as e:
        logger = get_logger(__name__)
        logger.error("Failed to stop scheduler: %s", e, exc_info=True)
        print(f"[ERROR] Failed to stop scheduler: {e}")
        exit(1)


if __name__ == "__main__":
    # Khởi tạo logging thống nhất cho toàn project
    setup_logging()
    logger = get_logger(__name__)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Threat Intelligence Pipeline - Collect and process IOCs from multiple feeds"
    )
    parser.add_argument(
        "--scheduler",
        action="store_true",
        help="Run in scheduler mode (automatically runs daily at work hours)"
    )
    parser.add_argument(
        "--stop-scheduler",
        action="store_true",
        help="Stop the running scheduler"
    )
    parser.add_argument(
        "--work-hour",
        type=int,
        default=8,
        help="Work hour for scheduler (default: 8)"
    )
    parser.add_argument(
        "--work-minute",
        type=int,
        default=0,
        help="Work minute for scheduler (default: 0)"
    )
    parser.add_argument(
        "--fetch-once",
        action="store_true",
        help="Fetch IOCs once and exit (for automation/scheduler)"
    )
    
    args = parser.parse_args()
    
    # Chọn chế độ chạy
    if args.fetch_once:
        # Chế độ tự động: chạy fetch một lần rồi thoát
        run_once()
    elif args.stop_scheduler:
        # Dừng scheduler đang chạy
        stop_scheduler()
    elif args.scheduler:
        # Chế độ scheduler: chạy tự động theo lịch
        run_scheduler(work_hour=args.work_hour, work_minute=args.work_minute)
    else:
        # Nếu không có flag, hiển thị menu tương tác cho người dùng
        def interactive_menu(default_hour: int = 8, default_minute: int = 0):
            """
            Menu đơn giản cho người dùng lựa chọn tác vụ:
            1) Chạy fetch một lần
            2) Bật scheduler (yêu cầu package `schedule`)
            3) Tắt scheduler
            4) Thoát
            """
            while True:
                print("\n=== ThreatFeedAggregator - Menu ===")
                print("1) Run fetch once")
                print("2) Start scheduler")
                print("3) Stop scheduler")
                print("4) Exit")
                print("5) Export last collected IOCs (from memory)")
                print("6) Export IOCs from DB")
                choice = input("Select an option [1-6]: ").strip()

                if choice == "1":
                    run_once()
                elif choice == "2":
                    try:
                        h = input(f"Work hour (default {default_hour}): ").strip()
                        m = input(f"Work minute (default {default_minute}): ").strip()
                        work_hour = int(h) if h else default_hour
                        work_minute = int(m) if m else default_minute
                    except ValueError:
                        print("[ERROR] Invalid hour/minute. Using defaults.")
                        work_hour, work_minute = default_hour, default_minute

                    print(f"[INFO] Starting scheduler at {work_hour:02d}:{work_minute:02d} (this will run until stopped)")
                    # Chú ý: hàm này sẽ không trở về cho đến khi scheduler dừng
                    run_scheduler(work_hour=work_hour, work_minute=work_minute)
                elif choice == "3":
                    stop_scheduler()
                elif choice == "4" or choice.lower() == "q":
                    print("Exiting.")
                    break
                elif choice == "5":
                    # xuất các IOC đã thu thập lần cuối từ bộ nhớ
                    if _last_iocs is None:
                        print("[INFO] No in-memory IOCs available. Run fetch first.")
                    else:
                        fmt = input("Format (csv|json|txt|jsonl|sqlite|all) [all]: ").strip() or "all"
                        exporter = IOCExporter(output_dir="output")
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        if fmt == "all":
                            res = exporter.export_all_formats(_last_iocs, base_filename=f"iocs_{ts}")
                            for k, v in res.items():
                                print(f"[✓] Saved ({k}): {v}")
                        elif fmt == "csv":
                            p = exporter.export_csv(_last_iocs, filename=f"iocs_{ts}.csv")
                            print(f"[✓] Saved (csv): {p}")
                        elif fmt == "json":
                            p = exporter.export_json(_last_iocs, filename=f"iocs_{ts}.json")
                            print(f"[✓] Saved (json): {p}")
                        elif fmt == "txt":
                            p = exporter.export_txt(_last_iocs, filename=f"iocs_{ts}.txt")
                            print(f"[✓] Saved (txt): {p}")
                        elif fmt == "jsonl":
                            p = exporter.export_jsonl(_last_iocs, filename=f"iocs_{ts}.jsonl")
                            print(f"[✓] Saved (jsonl): {p}")
                        elif fmt == "sqlite":
                            p = exporter.export_sqlite(_last_iocs, filename=f"iocs_{ts}.sqlite")
                            print(f"[✓] Saved (sqlite): {p}")
                        else:
                            print("[ERROR] Unsupported format.")
                elif choice == "6":
                    dbp = input("DB path (default data/database/ioc_database.db): ").strip() or None
                    fmt = input("Format (csv|json|txt|jsonl|sqlite|all) [csv]: ").strip() or "csv"
                    filename = input("Filename (optional): ").strip() or None
                    exporter = IOCExporter(output_dir="output")
                    try:
                        res = exporter.export_from_db(fmt=fmt, db_path=dbp, filename=filename)
                        if isinstance(res, dict):
                            for k, v in res.items():
                                print(f"[✓] Saved ({k}): {v}")
                        else:
                            print(f"[✓] Saved ({fmt}): {res}")
                    except Exception as e:
                        print(f"[ERROR] Failed export from DB: {e}")
                else:
                    print("Invalid option. Please choose 1-6.")

        interactive_menu(default_hour=args.work_hour, default_minute=args.work_minute)