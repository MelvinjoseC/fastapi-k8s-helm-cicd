"""OpenTelemetry distributed tracing configuration.
Provides seamless trace propagation and spans across HTTP, database, and cache calls.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from config import settings
from fastapi import FastAPI

logger = logging.getLogger("taskapi.tracing")


def setup_tracing(app: FastAPI) -> None:
    """Configures OpenTelemetry tracer and instruments FastAPI if enabled."""
    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing is disabled (OTEL_ENABLED=false).")
        return

    try:
        from database import engine
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create(
            {
                "service.name": settings.otel_service_name,
                "deployment.environment": settings.app_env,
            }
        )
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        SQLAlchemyInstrumentor().instrument(engine=engine, tracer_provider=provider)

        logger.info(
            "OpenTelemetry initialized with OTLP exporter at %s",
            settings.otel_exporter_otlp_endpoint,
        )
    except ImportError as exc:
        logger.warning(
            "OpenTelemetry packages not installed (%s). Tracing will remain inactive.",
            exc,
        )
    except Exception as exc:
        logger.error("Failed to initialize OpenTelemetry tracing: %s", exc)


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Generator[Any, None, None]:
    """Safe context manager to trace operations without hard dependency on OpenTelemetry."""
    if not settings.otel_enabled:
        yield None
        return

    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("taskapi")
        with tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, v)
            yield span
    except Exception:
        yield None
