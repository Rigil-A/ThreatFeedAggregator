from core.pipeline import ThreatIntelPipeline
from utils.logger_util import setup_logging, get_logger

import csv
from datetime import datetime


if __name__ == "__main__":
    # Khởi tạo logging thống nhất cho toàn project
    setup_logging()
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
        csv_file = f"output/iocs_{timestamp}.csv"
        
        # Sửa fieldnames để khớp với IOC.to_dict()
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, 
                fieldnames=["ioc", "type", "source", "feed_name", "metadata"]
            )
            writer.writeheader()
            for ioc in all_iocs:
                writer.writerow(ioc.to_dict())
        
        print(f"[✓] Saved {len(all_iocs)} IOCs to {csv_file}")
        # In 10 IOC đầu tiên
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