"""
SmartClaims -- OpenTelemetry Observability Module
=================================================
Initializes tracing and metrics once at import time.
- Production (APPLICATIONINSIGHTS_CONNECTION_STRING set): Azure Monitor
- Development: Console exporters
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env before reading config (idempotent, safe to double-call)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource

# --- Shared resource ---
resource = Resource.create({
    "service.name": "smartclaims-webapp",
    "service.version": "1.0.0",
    "deployment.environment": os.getenv("DEPLOYMENT_ENVIRONMENT", "dev"),
})

# --- Production vs Dev ---
_app_insights_cs = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

if _app_insights_cs:
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(
        connection_string=_app_insights_cs,
        resource=resource,
    )
else:
    _trace_provider = TracerProvider(resource=resource)
    _trace_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(_trace_provider)

    _metric_reader = PeriodicExportingMetricReader(
        ConsoleMetricExporter(),
        export_interval_millis=10_000,
    )
    _meter_provider = MeterProvider(resource=resource, metric_readers=[_metric_reader])
    metrics.set_meter_provider(_meter_provider)

# --- Tracer and Meter ---
tracer = trace.get_tracer("smartclaims.webapp", "1.0.0")
meter = metrics.get_meter("smartclaims.webapp", "1.0.0")

# --- Custom Metrics (from Lab 8) ---
request_counter = meter.create_counter(
    name="agent.request.count",
    description="Total number of agent requests",
    unit="requests",
)
latency_histogram = meter.create_histogram(
    name="agent.request.duration",
    description="Agent response time in seconds",
    unit="s",
)
token_counter = meter.create_counter(
    name="agent.tokens.used",
    description="Total tokens consumed by agent calls",
    unit="tokens",
)
active_sessions = meter.create_up_down_counter(
    name="agent.active_sessions",
    description="Number of currently active agent sessions",
    unit="sessions",
)
