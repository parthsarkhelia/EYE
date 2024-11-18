import logging
import time
import uuid

from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware

from src.secrets import secrets
from src.utils.formatter import trim


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_length = 1000  # Define maximum message length
        self.max_depth = 10  # Define maximum depth for trimming

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Custom fields
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logging_at"] = f"{record.pathname}:{record.lineno}"

        # Trimming and structuring the message
        if isinstance(record.msg, str):
            log_record["message"] = (
                record.msg[: self.max_length] + "..."
                if len(record.msg) > self.max_length
                else record.msg
            )
        elif isinstance(record.msg, dict):
            log_record.update(trim(item=record.msg, depth=0))

        # Handling latency calculation
        start_timestamp = log_record.get("start_timestamp")
        if start_timestamp:
            latency = time.time() - start_timestamp
            log_record["latency"] = (
                f"{latency:.3f} s" if latency >= 1 else f"{latency*1000:.0f} ms"
            )

        # Removing unwanted fields
        for field in ["start_timestamp"]:
            if field in log_record:
                del log_record[field]

        # Reordering keys
        priority_keys = [
            "timestamp",
            "level",
            "logging_at",
            "latency",
            "uuid",
            "path",
            "description",
            "event",
        ]
        ordered_log_record = {
            key: log_record[key] for key in priority_keys if key in log_record
        }

        # Add the remaining keys from the original log record
        for key, value in log_record.items():
            if key not in priority_keys:
                ordered_log_record[key] = value

        # Clear the original log record and update it with the ordered one
        log_record.clear()
        log_record.update(ordered_log_record)


def get_logging_level():
    log_level = secrets["logging_level"]
    return getattr(logging, log_level, logging.INFO)


def configure_logging():
    loggers = ("uvicorn.asgi", "uvicorn.access", "root")
    logging.basicConfig(handlers=[logging.StreamHandler()])
    formatter = CustomJsonFormatter()

    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(get_logging_level())
        for handler in logger.handlers:
            handler.setFormatter(formatter)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        context = {
            "uuid": str(uuid.uuid4()),
            "path": request.url.path,
            "start_timestamp": time.time(),
        }

        request.state.context = context
        response = None

        logging.info({**context, "event": "Request received"})
        try:
            response = await call_next(request)
        except Exception:
            logging.exception({**context, "event": "Processing Error"})
        logging.info({**context, "event": "Request completed"})

        return response


configure_logging()
