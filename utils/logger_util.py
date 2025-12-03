import logging
import os
from typing import Optional

DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FILE = "aggregator.log"


def setup_logging(
    log_dir: str = DEFAULT_LOG_DIR,
    log_file: str = DEFAULT_LOG_FILE,
    level: int = logging.INFO,
    to_console: bool = True,
) -> None:
    """
    Initialize a unified logging configuration for the whole project.

    - Create the log directory if needed.
    - Write logs to log_dir/log_file.
    - Optionally mirror output to the console.
    """
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    handlers = [logging.FileHandler(log_path, encoding="utf-8")]
    if to_console:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,  # ensure previous configs are overridden when re-called
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Retrieve a logger for modules or functions.
    Call setup_logging() once in the entry point before using this helper.
    """
    return logging.getLogger(name)


