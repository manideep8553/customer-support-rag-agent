import sys
import json
import logging
from pathlib import Path
from datetime import datetime

from backend.config import settings


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "request_path"):
            log_entry["request_path"] = record.request_path
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        return json.dumps(log_entry, default=str)


def setup_logging():
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    if settings.log_format == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
    root_logger.addHandler(console_handler)

    log_path = Path(settings.log_file)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                str(log_path),
                maxBytes=settings.log_file_max_size_mb * 1024 * 1024,
                backupCount=settings.log_file_backup_count,
            )
            file_handler.setFormatter(JSONFormatter())
            root_logger.addHandler(file_handler)
        except Exception as e:
            console_handler.stream.write(f"Warning: Could not set up file logging: {e}\n")

    for lib_logger in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(lib_logger).handlers.clear()
        logging.getLogger(lib_logger).propagate = True

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    root_logger.info("Logging configured: level=%s format=%s file=%s", settings.log_level, settings.log_format, settings.log_file)
