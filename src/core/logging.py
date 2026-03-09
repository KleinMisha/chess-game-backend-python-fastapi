import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from src.core.config import config

# Logging level is a integer enum: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL
LoggingLevel = int


ROOT_DIR = base_dir = Path(__file__).resolve().parent.parent.parent


def setup_logging(level: LoggingLevel) -> None:
    """Setup logging with output both to stdout and to a file."""
    logs_dir = ROOT_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)
    daily_log_file = logs_dir / f"{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=level,
        format=" | ".join(["%(asctime)s", "%(levelname)s", "%(name)s", "%(message)s"]),
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(daily_log_file, encoding="utf-8", mode="a"),
        ],
    )

    clear_old_logs(config.log_keep_days)


def clear_old_logs(keep_days: int) -> None:
    """Delete old log files (no need to keep all of them)."""
    oldest_to_keep = datetime.now() - timedelta(days=keep_days)
    for file in Path(ROOT_DIR / "logs").glob("*.log"):
        day_of_creation = datetime.strptime(file.stem, "%Y%m%d")
        if day_of_creation < oldest_to_keep:
            file.unlink()
