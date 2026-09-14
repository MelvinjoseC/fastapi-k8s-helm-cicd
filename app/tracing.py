"""OpenTelemetry distributed tracing configuration.
Provides seamless trace propagation and spans across HTTP, database, and cache calls.
"""
import logging
from typing import Optional
from fastapi import FastAPI

from config import settings

logger = logging.getLogger("taskapi.tracing")


def setup_tracing(app: FastAPI) -> None:
    """Configures OpenTelemetry tracer and instruments FastAPI if enabled."""
    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing is disabled (OTEL_ENABLED=false).")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
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