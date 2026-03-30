# Lab 8: Deep Observability — Tracing, Metrics & Monitoring

## What It Does
Builds a production-grade observability pipeline for AI agents using OpenTelemetry and Azure Monitor. Covers the three pillars (Traces, Metrics, Logs), custom instrumentation, nested spans, KQL queries, and alerting.

## Flow

```
  Set AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true (BEFORE SDK import)
    |
    v
  Configure OpenTelemetry
    |   TracerProvider (traces) + MeterProvider (metrics)
    |   Resource: service.name, version, environment
    |   Exporters: Console (lab) or Azure Monitor (production)
    |
    v
  Define Custom Metrics
    |   agent.request.count    — Counter
    |   agent.request.duration — Histogram (latency)
    |   agent.tokens.used      — Counter
    |   agent.active_sessions  — UpDownCounter
    |
    v
  observed_call() — Instrumented Agent Wrapper
    |   Creates a span per call with attributes:
    |     agent.name, version, model, tokens, duration, status
    |   Records metrics: latency, token count, success/failure
    |   Catches: AuthError, RateLimit, HTTP errors
    |
    v
  claims_workflow() — Nested Spans
    |   Parent: claims.workflow
    |     Child: input.validation   (check input)
    |     Child: agent.inference    (LLM call)
    |     Child: response.postprocess (check citations)
    |
    v
  Load Test → Telemetry Summary Report
    |   Latency: avg, min, max, p95
    |   Tokens: total input/output, avg per call
    |   Cost: session estimate, projected hourly/daily
    |
    v
  KQL Queries for Application Insights
    |   Latency percentiles, token usage, error rates, cost estimation
    |
    v
  Alerting Rules
      High latency, error spikes, token budget, auth failures
```

## Three Pillars of Observability

| Pillar | What It Captures | Azure Table |
|--------|-----------------|-------------|
| **Traces** | End-to-end request flow, nested spans | `dependencies`, `requests` |
| **Metrics** | Counters, histograms, gauges | `customMetrics` |
| **Logs** | Structured events, errors | `traces` |

## Key Concepts

- **OpenTelemetry** — vendor-neutral observability framework (CNCF standard)
- **TracerProvider + MeterProvider** — separate providers for traces and metrics
- **Resource** — identifies your service (name, version, environment) in all telemetry
- **Span attributes** — key-value pairs attached to each trace span (tokens, latency, status)
- **Nested spans** — break down multi-step workflows to find bottlenecks
- **observed_call()** — instrumented wrapper that captures traces + metrics + errors
- **KQL (Kusto Query Language)** — query language for Application Insights
- **Azure Monitor alerts** — automated rules for latency, errors, cost anomalies
- **Foundry portal tracing** — built-in trace viewer (no code needed, just env var)

## SDK Used

- `opentelemetry.sdk.trace.TracerProvider`, `SimpleSpanProcessor`, `ConsoleSpanExporter`
- `opentelemetry.sdk.metrics.MeterProvider`, `PeriodicExportingMetricReader`
- `opentelemetry.sdk.resources.Resource`
- `opentelemetry.trace.StatusCode` — OK, ERROR for span status
- `azure.monitor.opentelemetry.configure_azure_monitor` — production exporter
- `azure.core.exceptions.ClientAuthenticationError`, `HttpResponseError`

## Production Checklist

- Set `APPLICATIONINSIGHTS_CONNECTION_STRING` in `.env`
- Replace `ConsoleSpanExporter` with `configure_azure_monitor()`
- Pin KQL queries as Application Insights dashboard tiles
- Configure alert rules (latency, error rate, token budget)
- Enable Foundry portal tracing for development debugging
