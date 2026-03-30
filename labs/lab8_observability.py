"""
Lab 8: Deep Observability — Tracing, Metrics & Monitoring in Azure AI Foundry
===============================================================================
v2.x — OpenTelemetry traces + custom metrics + KQL query reference
Run: python labs/lab8_observability.py
"""

import sys
import os
import time
import json
from datetime import datetime, timezone

# MUST be set BEFORE importing SDK
os.environ["AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING"] = "true"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter, PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import StatusCode

from azure.ai.projects.models import PromptAgentDefinition
from azure.core.exceptions import HttpResponseError, ClientAuthenticationError
from utils.config import get_clients, MODEL, print_header, print_step


def main():
    print_header(8, "Deep Observability — Tracing, Metrics & Monitoring")

    # -- Step 1: Configure OpenTelemetry -------------------------
    print_step("Step 1: Configure OpenTelemetry (Traces + Metrics)")

    resource = Resource.create({
        "service.name": "smartclaims-agent",
        "service.version": "2.0.0",
        "deployment.environment": "lab",
    })

    # Traces → console
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(trace_provider)

    # Metrics → console (export every 10 seconds)
    metric_reader = PeriodicExportingMetricReader(
        ConsoleMetricExporter(),
        export_interval_millis=10_000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    tracer = trace.get_tracer("smartclaims.observability", "1.0.0")
    meter  = metrics.get_meter("smartclaims.observability", "1.0.0")

    print("   [OK] TracerProvider configured (console exporter)")
    print("   [OK] MeterProvider configured (console exporter, 10s interval)")
    print()
    print("   For production, use Azure Monitor:")
    print("     from azure.monitor.opentelemetry import configure_azure_monitor")
    print("     configure_azure_monitor(connection_string='InstrumentationKey=...')")

    project_client, openai_client = get_clients()

    # -- Step 2: Define Custom Metrics ---------------------------
    print_step("Step 2: Define Custom Metrics")

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

    print("   [OK] agent.request.count    (Counter)")
    print("   [OK] agent.request.duration (Histogram)")
    print("   [OK] agent.tokens.used      (Counter)")
    print("   [OK] agent.active_sessions  (UpDownCounter)")

    # -- Step 3: Instrumented Agent Call Wrapper ------------------
    print_step("Step 3: Instrumented Agent Call Wrapper")

    def observed_call(openai_client, agent, user_input, conversation_id=None):
        """
        Instrumented agent call — wraps every interaction with
        traces, metrics, and structured error handling.
        """
        common_attrs = {
            "agent.name": agent.name,
            "agent.version": str(agent.version),
            "model": MODEL,
        }

        with tracer.start_as_current_span("agent.call", attributes=common_attrs) as span:
            span.set_attribute("input.length", len(user_input))
            span.add_event("agent.call.start", {"user_input_preview": user_input[:100]})

            active_sessions.add(1, common_attrs)
            start_time = time.time()

            try:
                kwargs = {
                    "extra_body": {
                        "agent_reference": {
                            "name": agent.name,
                            "version": agent.version,
                            "type": "agent_reference",
                        }
                    },
                    "input": user_input,
                }
                if conversation_id:
                    kwargs["conversation"] = conversation_id

                response = openai_client.responses.create(**kwargs)
                duration = time.time() - start_time

                # Extract token usage
                input_tokens = getattr(response.usage, "input_tokens", 0) if response.usage else 0
                output_tokens = getattr(response.usage, "output_tokens", 0) if response.usage else 0
                total_tokens = input_tokens + output_tokens

                # Span attributes
                span.set_attribute("output.length", len(response.output_text))
                span.set_attribute("tokens.input", input_tokens)
                span.set_attribute("tokens.output", output_tokens)
                span.set_attribute("tokens.total", total_tokens)
                span.set_attribute("duration_seconds", round(duration, 3))
                span.set_attribute("status", "success")
                span.set_status(StatusCode.OK)
                span.add_event("agent.call.complete", {
                    "duration_ms": int(duration * 1000),
                    "total_tokens": total_tokens,
                })

                # Metrics
                request_counter.add(1, {**common_attrs, "status": "success"})
                latency_histogram.record(duration, common_attrs)
                if total_tokens > 0:
                    token_counter.add(total_tokens, common_attrs)

                return {
                    "ok": True,
                    "text": response.output_text,
                    "tokens": {"input": input_tokens, "output": output_tokens, "total": total_tokens},
                    "duration": round(duration, 3),
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                }

            except ClientAuthenticationError as e:
                duration = time.time() - start_time
                span.set_status(StatusCode.ERROR, "Authentication failed")
                span.record_exception(e)
                request_counter.add(1, {**common_attrs, "status": "auth_error"})
                latency_histogram.record(duration, common_attrs)
                return {"ok": False, "error": "Auth failed. Run: az login", "error_type": "auth"}

            except HttpResponseError as e:
                duration = time.time() - start_time
                error_type = "rate_limited" if e.status_code == 429 else f"http_{e.status_code}"
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                request_counter.add(1, {**common_attrs, "status": error_type})
                latency_histogram.record(duration, common_attrs)
                return {"ok": False, "error": f"HTTP {e.status_code}: {e.message}", "error_type": error_type}

            except Exception as e:
                duration = time.time() - start_time
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                request_counter.add(1, {**common_attrs, "status": "exception"})
                latency_histogram.record(duration, common_attrs)
                return {"ok": False, "error": str(e), "error_type": "exception"}

            finally:
                active_sessions.add(-1, common_attrs)

    print("   [OK] observed_call() defined — every agent call is now instrumented")

    # -- Step 4: Create Agent & Test Instrumented Calls -----------
    print_step("Step 4: Create Agent & Test Instrumented Calls")

    agent = project_client.agents.create_version(
        agent_name="smartclaims-observability",
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=(
                "You are SmartClaims, an insurance claims assistant. "
                "Be concise and helpful. Always cite policy sections when relevant."
            ),
        ),
    )
    print(f"   [OK] Agent created: {agent.name} v{agent.version}")

    test_queries = [
        "What is the deductible for auto collision claims?",
        "How long do I have to file a homeowner's claim after an incident?",
        "Explain the difference between comprehensive and collision coverage.",
    ]

    results = []
    for i, query in enumerate(test_queries, 1):
        print(f"\n   Query {i}: {query[:60]}...")
        result = observed_call(openai_client, agent, query)
        results.append(result)

        if result["ok"]:
            print(f"   [OK] Response: {result['text'][:100]}...")
            print(f"        Duration: {result['duration']}s | Tokens: {result['tokens']} | Trace: {result['trace_id']}")
        else:
            print(f"   [ERR] {result['error']}")

    # -- Step 5: Nested Spans — Multi-Step Workflow ---------------
    print_step("Step 5: Nested Spans — Multi-Step Workflow")

    def claims_workflow(openai_client, agent, user_input):
        """Full claims workflow with nested spans for each phase."""
        with tracer.start_as_current_span("claims.workflow") as parent_span:
            parent_span.set_attribute("workflow.type", "claims_query")
            workflow_start = time.time()

            # Phase 1: Input Validation
            with tracer.start_as_current_span("input.validation") as val_span:
                is_valid = len(user_input.strip()) > 0 and len(user_input) < 5000
                val_span.set_attribute("input.length", len(user_input))
                val_span.set_attribute("input.valid", is_valid)
                if not is_valid:
                    val_span.set_status(StatusCode.ERROR, "Invalid input")
                    return {"ok": False, "error": "Input validation failed"}

            # Phase 2: Agent Inference
            with tracer.start_as_current_span("agent.inference") as call_span:
                kwargs = {
                    "extra_body": {
                        "agent_reference": {
                            "name": agent.name,
                            "version": agent.version,
                            "type": "agent_reference",
                        }
                    },
                    "input": user_input,
                }
                call_start = time.time()
                response = openai_client.responses.create(**kwargs)
                call_duration = time.time() - call_start
                call_span.set_attribute("duration_seconds", round(call_duration, 3))
                input_tokens = getattr(response.usage, "input_tokens", 0) if response.usage else 0
                output_tokens = getattr(response.usage, "output_tokens", 0) if response.usage else 0
                call_span.set_attribute("tokens.total", input_tokens + output_tokens)

            # Phase 3: Post-Processing
            with tracer.start_as_current_span("response.postprocess") as post_span:
                output_text = response.output_text
                has_citation = any(kw in output_text.lower() for kw in ["section", "policy", "article", "clause"])
                post_span.set_attribute("has_citation", has_citation)
                post_span.set_attribute("response_length", len(output_text))

            total_duration = time.time() - workflow_start
            parent_span.set_attribute("workflow.duration", round(total_duration, 3))
            parent_span.set_status(StatusCode.OK)

            return {
                "ok": True,
                "text": output_text,
                "duration": round(total_duration, 3),
                "has_citation": has_citation,
                "trace_id": format(parent_span.get_span_context().trace_id, "032x"),
            }

    print("   [OK] claims_workflow() defined with nested spans")
    print()

    result = claims_workflow(
        openai_client, agent,
        "What documentation do I need to submit for a water damage claim on my home?"
    )

    if result["ok"]:
        print(f"   [OK] Workflow complete!")
        print(f"        Response: {result['text'][:120]}...")
        print(f"        Duration: {result['duration']}s | Citation: {result['has_citation']}")
        print(f"        Trace ID: {result['trace_id']}")
        print()
        print("   Nested spans emitted (check console output):")
        print("     1. input.validation  (child)")
        print("     2. agent.inference   (child)")
        print("     3. response.postprocess (child)")
        print("     4. claims.workflow   (parent)")
    else:
        print(f"   [ERR] {result['error']}")

    # -- Step 6: Load Test & Summary Report ----------------------
    print_step("Step 6: Load Test & Telemetry Summary")

    load_queries = [
        "What is the claims filing deadline?",
        "Do I need a police report for a theft claim?",
        "What's covered under comprehensive auto insurance?",
        "How do I appeal a denied claim?",
        "What is subrogation and how does it affect my claim?",
        "Can I get a rental car while my vehicle is being repaired?",
    ]

    print(f"   Running load test with {len(load_queries)} queries...\n")
    load_results = []
    for i, q in enumerate(load_queries, 1):
        r = observed_call(openai_client, agent, q)
        load_results.append(r)
        status = "[OK]" if r["ok"] else "[ERR]"
        duration = r.get("duration", 0)
        tokens = r.get("tokens", {}).get("total", 0)
        print(f"   {status} Q{i}: {duration}s | {tokens} tokens | {q[:45]}...")

    # Summary
    all_results = results + load_results
    successful = [r for r in all_results if r["ok"]]
    failed = [r for r in all_results if not r["ok"]]

    all_durations = [r["duration"] for r in successful]
    all_tokens = [r["tokens"]["total"] for r in successful]
    all_input_tokens = [r["tokens"]["input"] for r in successful]
    all_output_tokens = [r["tokens"]["output"] for r in successful]

    # Cost estimate (gpt-4o-mini pricing)
    COST_PER_1K_INPUT = 0.00015
    COST_PER_1K_OUTPUT = 0.0006
    total_cost = sum(
        (inp * COST_PER_1K_INPUT + out * COST_PER_1K_OUTPUT) / 1000
        for inp, out in zip(all_input_tokens, all_output_tokens)
    )

    print(f"\n{'='*60}")
    print(f"  OBSERVABILITY SUMMARY REPORT")
    print(f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    print()
    print(f"  Total Requests:     {len(all_results)}")
    print(f"  Successful:         {len(successful)} ({len(successful)/len(all_results)*100:.0f}%)")
    print(f"  Failed:             {len(failed)} ({len(failed)/len(all_results)*100:.0f}%)")
    print()
    print(f"  LATENCY")
    if all_durations:
        print(f"  |- Average:         {sum(all_durations)/len(all_durations):.3f}s")
        print(f"  |- Min:             {min(all_durations):.3f}s")
        print(f"  |- Max:             {max(all_durations):.3f}s")
        sorted_d = sorted(all_durations)
        p95_idx = int(len(sorted_d) * 0.95)
        print(f"  |- p95:             {sorted_d[min(p95_idx, len(sorted_d)-1)]:.3f}s")
    print()
    print(f"  TOKEN USAGE")
    if all_tokens:
        print(f"  |- Total Input:     {sum(all_input_tokens):,}")
        print(f"  |- Total Output:    {sum(all_output_tokens):,}")
        print(f"  |- Total:           {sum(all_tokens):,}")
        print(f"  |- Avg per call:    {sum(all_tokens)/len(all_tokens):,.0f}")
    print()
    print(f"  COST ESTIMATE (gpt-4o-mini)")
    print(f"  |- This session:    ${total_cost:.6f}")
    print(f"  |- Projected/hour:  ${total_cost * 60:.4f}")
    print(f"  |- Projected/day:   ${total_cost * 1440:.4f}")
    print(f"{'='*60}")

    # -- Step 7: KQL Queries Reference ---------------------------
    print_step("Step 7: KQL Queries for Application Insights")
    print()
    print("   When using Azure Monitor, query your telemetry with KQL:")
    print()
    print("   7.1 Agent Call Latency (p50/p95/p99):")
    print("     dependencies | where name == 'agent.call'")
    print("     | summarize p50=percentile(duration,50),")
    print("       p95=percentile(duration,95) by bin(timestamp,1h)")
    print()
    print("   7.2 Token Usage Over Time:")
    print("     dependencies | where name == 'agent.call'")
    print("     | extend tokens = toint(customDimensions['tokens.total'])")
    print("     | summarize sum(tokens) by bin(timestamp,1h)")
    print()
    print("   7.3 Error Rate by Type:")
    print("     dependencies | where name == 'agent.call'")
    print("     | extend status = tostring(customDimensions['status'])")
    print("     | summarize count() by status, bin(timestamp,1h)")
    print()
    print("   7.4 Cost Estimation:")
    print("     dependencies | where name == 'agent.call'")
    print("     | extend cost = toint(customDimensions['tokens.input'])*0.00000015")
    print("       + toint(customDimensions['tokens.output'])*0.0000006")
    print("     | summarize daily_cost=sum(cost) by bin(timestamp,1d)")

    # -- Step 8: Alerting Patterns --------------------------------
    print_step("Step 8: Recommended Alert Rules")
    print()
    print("   | Alert              | Condition                     | Severity |")
    print("   |--------------------|-------------------------------|----------|")
    print("   | High Latency       | p95 > 10s for 5 min          | Sev 2    |")
    print("   | Error Spike        | Error rate > 5% in 15 min    | Sev 1    |")
    print("   | Token Budget       | Daily tokens > 500K          | Sev 3    |")
    print("   | Auth Failures      | Any auth_error in 5 min      | Sev 1    |")
    print("   | Rate Limiting      | >3 rate_limited in 5 min     | Sev 2    |")

    # -- Step 9: Clean Up ----------------------------------------
    print_step("Step 9: Clean Up")
    try:
        project_client.agents.delete_agent("smartclaims-observability")
        print("   [OK] Deleted: smartclaims-observability")
    except Exception:
        print("   [SKIP] smartclaims-observability (already deleted)")

    trace_provider.force_flush()
    meter_provider.force_flush()
    print("   [OK] Telemetry flushed")

    print(f"\n{'='*65}")
    print("  [OK] Lab 8 Complete!")
    print("  Next: python labs/lab9_streaming.py")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
