from core.aggregator import ThreatFeedAggregator
from core.queue import File_queue
from core.db import create_tables, add_iocs_batch, insert_fetch_history, update_fetch_history, DB_PATH
from core.checkpoint import CheckpointManager
from utils.logger_util import get_logger
import sys
import os
import signal


class ThreatIntelPipeline:
    """
    1. Dùng ThreatFeedAggregator để fetch + parse + normalize IOC cho từng feed.
    2. Đẩy IOC đã chuẩn hóa vào hàng đợi File_queue (producer).
    3. Đọc hàng đợi và ghi IOC vào SQLite (consumer).
    """

    # Sau khi fetch + normalize, IOC sẽ được lưu tạm vào file queue đặt trong thư mục "data/processed" để đúng với cấu trúc thư mục
    def __init__(self, queue_path: str = "data/processed/ioc.queue", checkpoint_path: str = "data/processed/pipeline.checkpoint"):
        self.logger = get_logger(__name__)
        # Hàng đợi file-based
        self.queue = File_queue(queue_path)
        # Bộ thu thập IOC từ các feed
        self.aggregator = ThreatFeedAggregator()
        # Checkpoint manager để lưu trạng thái
        self.checkpoint = CheckpointManager(checkpoint_path)
        # Flag để theo dõi interrupt
        self._interrupted = False
        # Lưu lại các handler signal trước đó để có thể chuyển tiếp (quan trọng khi
        # scheduler cũng đăng ký handler). Điều này đảm bảo Ctrl+C sẽ dừng cả
        # pipeline và vòng lặp scheduler bên ngoài.
        try:
            self._prev_sigint_handler = signal.getsignal(signal.SIGINT)
            self._prev_sigterm_handler = signal.getsignal(signal.SIGTERM)
        except Exception:
            self._prev_sigint_handler = None
            self._prev_sigterm_handler = None

        # Đăng ký signal handler để lưu checkpoint khi bị interrupt
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Xử lý signal interrupt để lưu checkpoint trước khi thoát"""
        self.logger.warning("Received interrupt signal (Ctrl+C). Saving checkpoint...")
        self._interrupted = True
        # Checkpoint sẽ được lưu trong _drain_queue_to_db khi phát hiện _interrupted
        # Chuyển tiếp signal tới handler đã đăng ký trước đó (ví dụ handler của
        # scheduler) để vòng lặp bên ngoài cũng có thể phản ứng và dừng.
        try:
            # Chuyển tiếp SIGINT
            if signum == signal.SIGINT and self._prev_sigint_handler:
                # Tránh gọi đệ quy nếu handler trước đó là chính handler này
                if self._prev_sigint_handler not in (self._signal_handler, signal.SIG_DFL, signal.SIG_IGN):
                    try:
                        self._prev_sigint_handler(signum, frame)
                    except Exception:
                        pass
            # Chuyển tiếp SIGTERM
            if signum == signal.SIGTERM and self._prev_sigterm_handler:
                if self._prev_sigterm_handler not in (self._signal_handler, signal.SIG_DFL, signal.SIG_IGN):
                    try:
                        self._prev_sigterm_handler(signum, frame)
                    except Exception:
                        pass
        except Exception:
            pass

    def _enqueue_iocs(self, fetch_id: int):
        """
        Chạy qua tất cả feed đã enable, lấy IOC đã normalize
        và push từng item vào hàng đợi.
        Args:
            fetch_id: id của fetch_history được tạo trước khi fetch
        Trả về:
            - total_iocs: tổng số IOC đã push vào queue
            - collected_iocs: list IOC object (để cho main dùng nếu cần)
        """
        total_iocs = 0
        collected_iocs = []

        self.logger.info(
            "Enqueue IOCs from %d feeds... (fetch_id=%d)", len(self.aggregator.feeds), fetch_id
        )
        for feed in self.aggregator.feeds:
            if not getattr(feed, "enabled", False):
                self.logger.info("[SKIP] %s is disabled", feed.name)
                continue

            iocs = self.aggregator.process_feed(feed)

            for ioc in iocs:
                # Chỉ push dữ liệu tối thiểu cần cho DB
                item = {
                    "ioc_value": getattr(ioc, "value", None),
                    "ioc_type": getattr(ioc, "ioc_type", None),
                    "source": getattr(ioc, "source", None) or getattr(feed, "provider", None),
                    "fetch_id": fetch_id,  # Lưu fetch_id vào queue
                }

                # Bỏ qua IOC thiếu thông tin quan trọng
                if not item["ioc_value"] or not item["ioc_type"] or not item["source"]:
                    continue

                self.queue.push(item)
                total_iocs += 1
                collected_iocs.append(ioc)

        self.logger.info("Enqueued %d IOCs into queue.", total_iocs)
        return total_iocs, collected_iocs

    def _drain_queue_to_db(self, fetch_id: int, total_expected: int = None, resume: bool = False) -> int:
        """
        Đọc lần lượt từng item trong queue và ghi vào DB.
        Trả về tổng số IOC đã ghi vào DB.
        
        Args:
            fetch_id: id của fetch_history được tạo trước khi fetch
            total_expected: Tổng số IOC dự kiến trong queue
            resume: Nếu True, sẽ load checkpoint và tiếp tục từ điểm đã dừng
        """
        total_written = 0
        total_errors = 0
        processed = 0
        
        # Load checkpoint nếu resume
        if resume:
            checkpoint_data = self.checkpoint.load()
            if checkpoint_data:
                processed = checkpoint_data.get("processed", 0)
                total_written = checkpoint_data.get("total_written", 0)
                total_errors = checkpoint_data.get("total_errors", 0)
                self.logger.info(
                    "Resuming from checkpoint: processed=%d, written=%d, errors=%d",
                    processed, total_written, total_errors
                )
        
        # Nếu caller đã biết trước tổng số item enqueue, dùng giá trị đó để tránh đọc lại file queue.
        if total_expected is not None:
            total = int(total_expected)
        else:
            # Nếu không biết, gọi self.queue.size()
            try:
                total = self.queue.size() or 0
            except Exception:
                total = 0

        self.logger.info("Start draining queue to database... total_queue_items=%d, fetch_id=%d", total, fetch_id)

        # Tối ưu: sử dụng batch pop để giảm số lần đọc/ghi file queue
        pop_batch_size = 5000  # Pop 5000 items mỗi lần từ queue
        db_batch_size = 1000  # Ghi 1000 items mỗi lần vào DB
        checkpoint_interval = 1000  # Lưu checkpoint mỗi 1000 items đã xử lý

        try:
            while True:
                # Kiểm tra interrupt flag
                if self._interrupted:
                    self.logger.warning("Interrupt detected. Saving checkpoint and exiting...")
                    self.checkpoint.save(processed, total_written, total_errors)
                    self.logger.info(
                        "Checkpoint saved: processed=%d, written=%d, errors=%d. "
                        "Run again to resume from this point.",
                        processed, total_written, total_errors
                    )
                    break
                
                # Pop một batch lớn từ queue (chỉ đọc/ghi file 1 lần)
                items = self.queue.pop_batch(pop_batch_size)
                if not items:
                    break

                # Validate và lọc items hợp lệ
                valid_items = []
                for item in items:
                    ioc_value = item.get("ioc_value")
                    ioc_type = item.get("ioc_type")
                    source = item.get("source")

                    if not ioc_value or not ioc_type or not source:
                        total_errors += 1
                        continue

                    valid_items.append(item)
                    processed += 1

                # Ghi vào DB theo batch nhỏ hơn
                for i in range(0, len(valid_items), db_batch_size):
                    batch = valid_items[i:i + db_batch_size]
                    try:
                        # Lấy fetch_id từ item đầu tiên (tất cả item đều có fetch_id giống nhau)
                        batch_fetch_id = batch[0].get("fetch_id", fetch_id) if batch else fetch_id
                        written_in_batch = add_iocs_batch(batch, batch_fetch_id)
                        total_written += written_in_batch
                    except Exception as e:
                        total_errors += len(batch)
                        self.logger.error(
                            "Failed to write batch to DB: batch_size=%d, error=%s",
                            len(batch), e,
                            exc_info=True
                        )

                # Cập nhật tiến độ thường xuyên hơn
                if total and total > 0:
                    update_interval = max(total // 100, 1)  # Cập nhật mỗi 1%
                    should_update = (processed % update_interval == 0) or (processed == total)
                else:
                    # Không biết tổng -> cập nhật mỗi 1000 bản ghi
                    should_update = (processed % 1000 == 0)

                if should_update:
                    if total and total > 0:
                        percent = (processed / total) * 100
                        msg = f"DB progress: {processed}/{total} ({percent:.1f}%) - Written: {total_written}"
                    else:
                        msg = f"DB progress: {processed}/? - Written: {total_written}"
                    try:
                        sys.stdout.write('\r' + msg)
                        sys.stdout.flush()
                    except Exception:
                        self.logger.info("%s", msg)

                if total_written % 5000 == 0 and total_written > 0:
                    self.logger.info("Written %d IOCs to database so far...", total_written)
                
                # Lưu checkpoint định kỳ
                if processed % checkpoint_interval == 0 and processed > 0:
                    self.checkpoint.save(processed, total_written, total_errors)
        
        except KeyboardInterrupt:
            # Xử lý KeyboardInterrupt trực tiếp (backup)
            self.logger.warning("KeyboardInterrupt detected. Saving checkpoint...")
            self.checkpoint.save(processed, total_written, total_errors)
            self.logger.info(
                "Checkpoint saved: processed=%d, written=%d, errors=%d",
                processed, total_written, total_errors
            )
            raise
        
        finally:
            # Xóa checkpoint nếu đã xử lý xong (queue rỗng và không bị interrupt)
            if not self._interrupted and not self.queue.has_data():
                self.checkpoint.clear()
                self.logger.info("Queue drained completely. Checkpoint cleared.")

        # Kết thúc dòng tiến độ, xuống dòng
        try:
            if total or processed:
                sys.stdout.write('\n')
                sys.stdout.flush()
        except Exception:
            pass

        if total_errors > 0:
            self.logger.warning("Encountered %d errors while writing to database", total_errors)
        
        # Cập nhật fetch_history với thống kê cuối cùng
        self.logger.info("Updating fetch_history (fetch_id=%d) with final statistics", fetch_id)
        update_fetch_history(
            fetch_id,
            total_src=1,  # Số nguồn feed
            total_ioc=total_written + total_errors,  # Tổng số IOC đã xử lý
            new_ioc=total_written  # Số IOC mới được thêm vào
        )
        
        self.logger.info("Written %d IOCs to database (errors: %d).", total_written, total_errors)
        return total_written

    def run(self, skip_enqueue_if_exists: bool = True, auto_resume: bool = False):
        """
        - Kiểm tra queue đã tồn tại chưa, nếu có thì hỏi người dùng có muốn tiếp tục không.
        - Tạo bảng DB nếu chưa tồn tại.
        - Tạo fetch_history record vào đầu tiên.
        - Fetch + normalize IOCs từ tất cả feed và đưa vào queue (nếu chưa có).
        - Đẩy toàn bộ queue vào DB.
        Trả về tuple: (số_feed, tổng_ioc_enqueue, tổng_ioc_ghi_db, list_ioc_object)
        
        Args:
            skip_enqueue_if_exists: Nếu True và queue đã có dữ liệu, sẽ hỏi người dùng có muốn bỏ qua bước enqueue không
            auto_resume: Nếu True, tự động resume từ queue/checkpoint mà không hỏi người dùng (dùng cho scheduler)
        """
        try:
            # Đảm bảo thư mục database tồn tại
            db_dir = os.path.dirname(DB_PATH)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                self.logger.info("Created database directory: %s", db_dir)
            
            # Đảm bảo DB đã sẵn sàn
            self.logger.info("Initializing database...")
            create_tables()
            self.logger.info("Database initialized successfully.")
            
            # Tạo fetch history record VÀO ĐẦU TIÊN - trước khi fetch
            # Điều này đảm bảo tất cả IOC được fetch sẽ được ghi với cùng 1 fetch_id
            self.logger.info("Creating fetch history record...")
            fetch_id = insert_fetch_history(
                total_src=0,  # Sẽ cập nhật sau
                total_ioc=0,  # Sẽ cập nhật sau
                new_ioc=0     # Sẽ cập nhật sau
            )
            self.logger.info("Created fetch history with fetch_id=%d", fetch_id)

            # Kiểm tra queue đã tồn tại và có dữ liệu chưa
            queue_exists = self.queue.has_data()
            resume = False
            # Flag để theo dõi xem có vừa enqueue không
            enqueued_now = False
            
            if queue_exists:
                queue_size = self.queue.size()
                self.logger.info("Found existing queue with %d items", queue_size)
                print(f"\n[INFO] Found existing queue with {queue_size} IOCs.")
                
                # Kiểm tra checkpoint
                checkpoint_info = ""
                if self.checkpoint.exists():
                    checkpoint_data = self.checkpoint.load()
                    if checkpoint_data:
                        processed = checkpoint_data.get("processed", 0)
                        written = checkpoint_data.get("total_written", 0)
                        errors = checkpoint_data.get("total_errors", 0)
                        checkpoint_info = (
                            f"\n[INFO] Found checkpoint:\n"
                            f"  - Processed: {processed} IOCs\n"
                            f"  - Written to DB: {written} IOCs\n"
                            f"  - Errors: {errors}\n"
                            f"[INFO] You can resume from this point."
                        )
                        print(checkpoint_info)
                
                if skip_enqueue_if_exists:
                    if auto_resume:
                        # Chế độ tự động: tự động resume từ queue/checkpoint
                        self.logger.info("Auto-resume mode: automatically resuming from existing queue")
                        resume = True
                        total_enqueued = queue_size
                        collected_iocs = []  # Không có collected_iocs khi resume
                    else:
                        # Chế độ tương tác: hỏi người dùng
                        print("\n[OPTIONS]")
                        print("1. Continue writing to database from existing queue (resume)")
                        print("2. Skip, do nothing")
                        print("3. Clear queue and start fresh")
                        response = input("\nChoose (1/2/3) [default: 1]: ").strip()

                        if response == '3':
                            # Xóa queue và checkpoint
                            if os.path.exists(self.queue.queue_path):
                                os.remove(self.queue.queue_path)
                            self.checkpoint.clear()
                            self.logger.info("Queue and checkpoint cleared. Starting fresh.")
                            print("[INFO] Queue and checkpoint cleared. Starting fresh.")
                            total_enqueued, collected_iocs = self._enqueue_iocs(fetch_id)
                            enqueued_now = True
                        elif response == '2':
                            self.logger.info("User chose to skip. Exiting.")
                            print("[INFO] Skipped. Queue remains unchanged.")
                            return 0, queue_size, 0, []
                        else:
                            # Mặc định: resume
                            resume = True
                            total_enqueued = queue_size
                            collected_iocs = []  # Không có collected_iocs khi resume
                else:
                    # Vẫn enqueue nhưng sẽ append vào queue hiện có
                    total_enqueued, collected_iocs = self._enqueue_iocs(fetch_id)
                    enqueued_now = True
            else:
                # Queue chưa tồn tại hoặc rỗng, tiến hành enqueue bình thường
                total_enqueued, collected_iocs = self._enqueue_iocs(fetch_id)
                enqueued_now = True
            
            # Drain queue và ghi vào DB. Nếu biết tổng (total_enqueued), truyền vào để tránh đọc lại file queue lớn.
            # Nếu vừa enqueue, chạy phân tích queue trước khi đẩy vào DB
            if enqueued_now:
                try:
                    from analyze import analyze_queue
                    self.logger.info("Running analyze_queue() after enqueue...")
                    try:
                        analyze_ok = analyze_queue()
                        if not analyze_ok:
                            self.logger.warning("analyze_queue returned False or failed")
                    except Exception as e:
                        self.logger.error("analyze_queue raised exception: %s", e, exc_info=True)
                except Exception as e:
                    self.logger.warning("Could not import/run analyze_queue: %s", e)

            total_written = self._drain_queue_to_db(fetch_id, total_expected=total_enqueued, resume=resume)
            
            feed_count = len(self.aggregator.feeds)
            
            self.logger.info(
                "Pipeline completed: feeds=%d, enqueued=%d, written=%d, collected=%d",
                feed_count, total_enqueued, total_written, len(collected_iocs)
            )

            return feed_count, total_enqueued, total_written, collected_iocs
            
        except Exception as e:
            self.logger.error("Pipeline failed with error: %s", e, exc_info=True)
            raise


