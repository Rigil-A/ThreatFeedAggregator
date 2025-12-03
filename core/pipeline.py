from core.aggregator import ThreatFeedAggregator
from core.queue import File_queue
from core.db import create_table, add_ioc, DB_PATH
from utils.logger_util import get_logger
import sys
import os


class ThreatIntelPipeline:
    """
    1. Dùng ThreatFeedAggregator để fetch + parse + normalize IOC cho từng feed.
    2. Đẩy IOC đã chuẩn hóa vào hàng đợi File_queue (producer).
    3. Đọc hàng đợi và ghi IOC vào SQLite (consumer).
    """

    # Sau khi fetch + normalize, IOC sẽ được lưu tạm vào file queue đặt trong thư mục "data/processed" để đúng với cấu trúc thư mục
    def __init__(self, queue_path: str = "data/processed/ioc.queue"):
        self.logger = get_logger(__name__)
        # Hàng đợi file-based
        self.queue = File_queue(queue_path)
        # Bộ thu thập IOC từ các feed
        self.aggregator = ThreatFeedAggregator()

    def _enqueue_iocs(self):
        """
        Chạy qua tất cả feed đã enable, lấy IOC đã normalize
        và push từng item vào hàng đợi.
        Trả về:
            - total_iocs: tổng số IOC đã push vào queue
            - collected_iocs: list IOC object (để cho main dùng nếu cần)
        """
        total_iocs = 0
        collected_iocs = []

        self.logger.info(
            "Enqueue IOCs from %d feeds...", len(self.aggregator.feeds)
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
                }

                # Bỏ qua IOC thiếu thông tin quan trọng
                if not item["ioc_value"] or not item["ioc_type"] or not item["source"]:
                    continue

                self.queue.push(item)
                total_iocs += 1
                collected_iocs.append(ioc)

        self.logger.info("Enqueued %d IOCs into queue.", total_iocs)
        return total_iocs, collected_iocs

    def _drain_queue_to_db(self, total_expected: int = None) -> int:
        """
        Đọc lần lượt từng item trong queue và ghi vào DB.
        Trả về tổng số IOC đã ghi vào DB.
        """
        total_written = 0
        total_errors = 0
        # Nếu caller đã biết trước tổng số item enqueue, dùng giá trị đó để tránh đọc lại file queue.
        if total_expected is not None:
            total = int(total_expected)
        else:
            # Nếu không biết, gọi self.queue.size()
            try:
                total = self.queue.size() or 0
            except Exception:
                total = 0

        processed = 0
        self.logger.info("Start draining queue to database... total_queue_items=%d", total)

        while True:
            item = self.queue.pop()
            if item is None:
                break

            # Validate dữ liệu trước khi ghi
            ioc_value = item.get("ioc_value")
            ioc_type = item.get("ioc_type")
            source = item.get("source")

            if not ioc_value or not ioc_type or not source:
                self.logger.warning(
                    "Skipping invalid item from queue: ioc_value=%s, ioc_type=%s, source=%s",
                    ioc_value, ioc_type, source
                )
                total_errors += 1
                continue

            try:
                add_ioc(
                    ioc_value=ioc_value,
                    ioc_type=ioc_type,
                    source=source,
                )
                total_written += 1
                processed += 1

                # Cập nhật tiến độ trên một dòng console bằng carriage return.
                # Tổng IOC dự kiến rất lớn nên cập nhật mỗi 1%.
                if total and total > 0:
                    update_interval = max(total // 100, 1)  # tương đương 1%
                    should_update = (processed % update_interval == 0) or (processed == total)
                else:
                    # Không biết tổng -> cập nhật mỗi 100 bản ghi (fallback).
                    should_update = (processed % 100 == 0)

                if should_update:
                    if total and total > 0:
                        percent = (processed / total) * 100
                        msg = f"DB progress: {processed}/{total} ({percent:.1f}%)"
                    else:
                        msg = f"DB progress: {processed}/?"
                    try:
                        sys.stdout.write('\r' + msg)
                        sys.stdout.flush()
                    except Exception:
                        self.logger.info("%s", msg)

                if total_written % 100 == 0:
                    self.logger.debug("Written %d IOCs to database so far...", total_written)
            except Exception as e:
                total_errors += 1
                self.logger.error(
                    "Failed to write IOC to DB: ioc_value=%s, ioc_type=%s, source=%s, error=%s",
                    ioc_value, ioc_type, source, e,
                    exc_info=True
                )

        # Kết thúc dòng tiến độ, xuống dòng
        try:
            if total or processed:
                sys.stdout.write('\n')
                sys.stdout.flush()
        except Exception:
            pass

        if total_errors > 0:
            self.logger.warning("Encountered %d errors while writing to database", total_errors)
        
        self.logger.info("Written %d IOCs to database (errors: %d).", total_written, total_errors)
        return total_written

    def run(self):
        """
        - Tạo bảng DB nếu chưa tồn tại.
        - Fetch + normalize IOCs từ tất cả feed và đưa vào queue.
        - Đẩy toàn bộ queue vào DB.
        Trả về tuple: (số_feed, tổng_ioc_enqueue, tổng_ioc_ghi_db, list_ioc_object)
        """
        try:
            # Đảm bảo thư mục database tồn tại
            db_dir = os.path.dirname(DB_PATH)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                self.logger.info("Created database directory: %s", db_dir)
            
            # Đảm bảo DB đã sẵn sàng
            self.logger.info("Initializing database...")
            create_table()
            self.logger.info("Database initialized successfully.")

            # Enqueue IOCs từ các feed
            total_enqueued, collected_iocs = self._enqueue_iocs()
            
            # Drain queue và ghi vào DB. Nếu biết tổng (total_enqueued), truyền vào để tránh đọc lại file queue lớn.
            total_written = self._drain_queue_to_db(total_expected=total_enqueued)
            
            feed_count = len(self.aggregator.feeds)
            
            self.logger.info(
                "Pipeline completed: feeds=%d, enqueued=%d, written=%d, collected=%d",
                feed_count, total_enqueued, total_written, len(collected_iocs)
            )

            return feed_count, total_enqueued, total_written, collected_iocs
            
        except Exception as e:
            self.logger.error("Pipeline failed with error: %s", e, exc_info=True)
            raise


