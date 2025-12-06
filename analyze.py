<<<<<<< HEAD
import json
import sys
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib

from utils.logger_util import get_logger

matplotlib.use('Agg')

# Khởi tạo logger
logger = get_logger(__name__)
QUEUE_PATH = "data/processed/ioc.queue"


def analyze_queue():
    """
    Đọc file queue và phân tích phân bố IOC type.
    Tạo bảng thống kê và biểu đồ.
    """
    ioc_types = Counter()
    total_items = 0
    errors = 0

    logger.info("Starting IOC queue analysis: %s", QUEUE_PATH)

    try:
        with open(QUEUE_PATH, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    item = json.loads(line)
                    ioc_type = item.get('ioc_type')
                    if ioc_type:
                        ioc_types[ioc_type] += 1
                    total_items += 1

                    # Cập nhật tiến độ mỗi 50k dòng
                    if line_num % 50000 == 0:
                        msg = f"Processed: {line_num:,} lines..."
                        try:
                            sys.stdout.write(f'\r{msg}')
                            sys.stdout.flush()
                        except Exception:
                            logger.info(msg)

                except json.JSONDecodeError:
                    errors += 1
                    if errors <= 3:
                        logger.warning("JSON decode error at line %d", line_num)

    except Exception as e:
        logger.error("Failed to read queue file: %s", e, exc_info=True)
        return False

    # Tổng kết
    total_sorted = sorted(ioc_types.items(), key=lambda x: x[1], reverse=True)

    logger.info("IOC queue analysis finished: total=%d, errors=%d", total_items, errors)

    # Bảng trong terminal
    print(f"Total items: {total_items} | JSON errors: {errors}")
    print("IOC Type                  Count    Percentage")
    for ioc_type, count in total_sorted:
        percentage = (count / total_items * 100) if total_items > 0 else 0
        print(f"{ioc_type:22s} {count:8,d} {percentage:8.2f}%")

    # Tạo biểu đồ
    if len(ioc_types) > 0:
        types_list = [t[0] for t in total_sorted]
        counts_list = [t[1] for t in total_sorted]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Biểu đồ tròn
        ax1.pie(counts_list, labels=types_list, autopct='%1.1f%%', startangle=90)
        ax1.set_title('IOC Types (pie)')

        # Biểu đồ cột
        ax2.bar(types_list, counts_list)
        ax2.set_xlabel('IOC Type')
        ax2.set_ylabel('Count')
        ax2.set_title('IOC Types (bar)')
        ax2.grid(axis='y', alpha=0.2)

        # Định dạng trục y với dấu phẩy
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

        # Xoay nhãn x nếu có quá nhiều loại
        if len(types_list) > 5:
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')

        plt.tight_layout()

        # Lưu biểu đồ
        output_path = "output/ioc_types_chart.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info("Chart saved: %s", output_path)
        plt.close()
    else:
        logger.info("No IOC types to chart")

    logger.info("Analysis completed")
    return True

if __name__ == "__main__":
    success = analyze_queue()
    sys.exit(0 if success else 1)
=======
import json
import sys
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib

from utils.logger_util import get_logger

matplotlib.use('Agg')

# Khởi tạo logger
logger = get_logger(__name__)
QUEUE_PATH = "data/processed/ioc.queue"


def analyze_queue():
    """
    Đọc file queue và phân tích phân bố IOC type.
    Tạo bảng thống kê và biểu đồ.
    """
    ioc_types = Counter()
    total_items = 0
    errors = 0

    logger.info("Starting IOC queue analysis: %s", QUEUE_PATH)

    try:
        with open(QUEUE_PATH, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    item = json.loads(line)
                    ioc_type = item.get('ioc_type')
                    if ioc_type:
                        ioc_types[ioc_type] += 1
                    total_items += 1

                    # Cập nhật tiến độ mỗi 50k dòng
                    if line_num % 50000 == 0:
                        msg = f"Processed: {line_num:,} lines..."
                        try:
                            sys.stdout.write(f'\r{msg}')
                            sys.stdout.flush()
                        except Exception:
                            logger.info(msg)

                except json.JSONDecodeError:
                    errors += 1
                    if errors <= 3:
                        logger.warning("JSON decode error at line %d", line_num)

    except Exception as e:
        logger.error("Failed to read queue file: %s", e, exc_info=True)
        return False

    # Tổng kết
    total_sorted = sorted(ioc_types.items(), key=lambda x: x[1], reverse=True)

    logger.info("IOC queue analysis finished: total=%d, errors=%d", total_items, errors)

    # Bảng trong terminal
    print(f"Total items: {total_items} | JSON errors: {errors}")
    print("IOC Type                  Count    Percentage")
    for ioc_type, count in total_sorted:
        percentage = (count / total_items * 100) if total_items > 0 else 0
        print(f"{ioc_type:22s} {count:8,d} {percentage:8.2f}%")

    # Tạo biểu đồ
    if len(ioc_types) > 0:
        types_list = [t[0] for t in total_sorted]
        counts_list = [t[1] for t in total_sorted]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Biểu đồ tròn
        ax1.pie(counts_list, labels=types_list, autopct='%1.1f%%', startangle=90)
        ax1.set_title('IOC Types (pie)')

        # Biểu đồ cột
        ax2.bar(types_list, counts_list)
        ax2.set_xlabel('IOC Type')
        ax2.set_ylabel('Count')
        ax2.set_title('IOC Types (bar)')
        ax2.grid(axis='y', alpha=0.2)

        # Định dạng trục y với dấu phẩy
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

        # Xoay nhãn x nếu có quá nhiều loại
        if len(types_list) > 5:
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')

        plt.tight_layout()

        # Lưu biểu đồ
        output_path = "output/ioc_types_chart.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info("Chart saved: %s", output_path)
        plt.close()
    else:
        logger.info("No IOC types to chart")

    logger.info("Analysis completed")
    return True

if __name__ == "__main__":
    success = analyze_queue()
    sys.exit(0 if success else 1)
>>>>>>> dcdebcb (Add scheduler, checkpoint, data analyzer function. Improve database writing speed)
