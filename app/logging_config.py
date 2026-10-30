"""Structured logging configuration for production workloads.
Outputs JSON formatted logs in production or human-readable logs in development.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id_ctx", default=None)
client_ip_ctx: ContextVar[str | None] = ContextVar("client_ip_ctx", default=None)
user_agent_ctx: ContextVar[str | None] = ContextVar("user_agent_ctx", default=None)


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        cid = correlation_id_ctx.get()
        if cid:
            log_obj["correlation_id"] = cid

        client_ip = client_ip_ctx.get()
        if client_ip:
            log_obj["client_ip"] = client_ip

        ua = user_agent_ctx.get()
        if ua:
            log_obj["user_agent"] = ua

        # Attempt to read active OpenTelemetry trace ID if present
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx.is_valid:
                log_obj["trace_id"] = f"{ctx.trace_id:032x}"
                log_obj["span_id"] = f"{ctx.span_id:016x}"
        except Exception:
            pass

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configures root and application loggers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if log_format.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
            )
        )
    root_logger.addHandler(handler)
