"""
Lab 9: Streaming Responses — Real-Time Agent UX
=================================================
Token-by-token output and streaming with function tools.
Run: python labs/lab9_streaming.py
"""

import sys
import os
import json
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import get_clients, MODEL, print_header, print_step
from utils.business_functions import get_claim_status, calculate_fraud_risk
from azure.ai.projects.models import PromptAgentDefinition


# --------------------------------------------------
# Function tools (reused from Lab 5)
# --------------------------------------------------
FUNCTION_MAP = {
    "get_claim_status": get_claim_status,
    "calculate_fraud_risk": calculate_fraud_risk,
}

FUNCTION_TOOLS = [
    {
        "type": "function",
        "name": "get_claim_status",
        "description": (
            "Look up the current status of an insurance claim by ID. "
            "Returns claim details including status, amount, adjuster, "
            "and fraud score."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Claim ID in CLM-XXXX format"
                }
            },
            "required": ["claim_id"]
        }
    },
    {
        "type": "function",
        "name": "calculate_fraud_risk",
        "description": (
            "Calculate fraud risk score for a new insurance claim."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "incident_type": {
                    "type": "string",
                    "enum": [
                        "Auto Collision", "Property Damage",
                        "Medical Claim", "Theft",
                        "Natural Disaster", "Liability",
                        "Fire Damage"
                    ]
                },
                "claim_amount": {"type": "number"},
                "region": {
                    "type": "string",
                    "enum": ["North", "South", "East", "West", "Central"]
                },
                "days_since_policy_start": {"type": "integer"}
            },
            "required": [
                "incident_type", "claim_amount",
                "region", "days_since_policy_start"
            ]
        }
    },
]


def main():
    print_header(9, "Streaming Responses — Real-Time Agent UX")
    project_client, openai_client = get_clients()

    # -- Step 1: Basic Streaming Response -------------------
    print_step("Step 1: Basic Streaming — Token by Token")

    agent = project_client.agents.create_version(
        agent_name="smartclaims-stream",
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=(
                "You are SmartClaims, a helpful insurance assistant. "
                "Keep responses concise (2-3 sentences max)."
            ),
        ),
    )
    print(f"   Agent: {agent.name} v{agent.version}")
    print()

    query = "What are the top 3 things a customer should do immediately after a car accident?"
    print(f"   User: {query}")
    print(f"   Agent: ", end="", flush=True)

    stream = openai_client.responses.create(
        extra_body={
            "agent_reference": {
                "name": agent.name,
                "version": agent.version,
                "type": "agent_reference",
            }
        },
        input=query,
        stream=True,
    )

    for event in stream:
        event_type = event.type if hasattr(event, "type") else type(event).__name__
        if event_type == "response.output_text.delta":
            print(event.delta, end="", flush=True)

    print()  # newline after streaming

    # -- Step 2: Stream Event Anatomy -----------------------
    print_step("Step 2: Stream Event Anatomy")

    query2 = "What does comprehensive auto insurance cover?"
    print(f"   Streaming: \"{query2}\"")
    print()

    event_counts = {}
    first_text_time = None
    start_time = time.time()

    stream2 = openai_client.responses.create(
        extra_body={
            "agent_reference": {
                "name": agent.name,
                "version": agent.version,
                "type": "agent_reference",
            }
        },
        input=query2,
        stream=True,
    )

    for event in stream2:
        event_type = event.type if hasattr(event, "type") else type(event).__name__
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
        if event_type == "response.output_text.delta" and first_text_time is None:
            first_text_time = time.time()

    end_time = time.time()

    print(f"   {'Event Type':<50s} | {'Count':>5s}")
    print(f"   {'-'*50}-+-{'-'*5}")
    for etype, count in sorted(event_counts.items()):
        print(f"   {etype:<50s} | {count:>5d}")
    print()

    if first_text_time:
        ttft = first_text_time - start_time
        total = end_time - start_time
        print(f"   Time to first token: {ttft:.2f}s")
        print(f"   Total stream time:   {total:.2f}s")

    # -- Step 3: Streaming with Function Tools --------------
    print_step("Step 3: Streaming with Function Calls")

    # Create agent with function tools
    agent_fn = project_client.agents.create_version(
        agent_name="smartclaims-stream-fn",
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=(
                "You are SmartClaims Operations Agent. Use your tools "
                "to look up claims and assess fraud risk. Be concise."
            ),
            tools=FUNCTION_TOOLS,
        ),
    )
    print(f"   Agent: {agent_fn.name} v{agent_fn.version}")

    query3 = "Look up claim CLM-0042 and tell me its status."
    print(f"\n   User: {query3}")
    print(f"   Agent: ", end="", flush=True)

    # First streaming call
    conv = openai_client.conversations.create()
    stream3 = openai_client.responses.create(
        conversation=conv.id,
        extra_body={
            "agent_reference": {
                "name": agent_fn.name,
                "version": agent_fn.version,
                "type": "agent_reference",
            }
        },
        input=query3,
        stream=True,
    )

    # Collect events and detect function calls
    function_calls = []
    response_id = None
    full_text = ""

    for event in stream3:
        event_type = event.type if hasattr(event, "type") else type(event).__name__

        if event_type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
            full_text += event.delta

        elif event_type == "response.function_call_arguments.done":
            function_calls.append({
                "name": event.name,
                "arguments": event.arguments,
                "call_id": event.call_id,
            })
            print(f"\n   [TOOL CALL] {event.name}({event.arguments})")

        elif event_type == "response.completed":
            response_id = event.response.id if hasattr(event, "response") else None

    # If function calls were made, execute and continue streaming
    if function_calls and response_id:
        tool_outputs = []
        for fc in function_calls:
            func = FUNCTION_MAP.get(fc["name"])
            if func:
                args = json.loads(fc["arguments"])
                result = func(**args)
            else:
                result = json.dumps({"error": f"Unknown: {fc['name']}"})

            tool_outputs.append({
                "type": "function_call_output",
                "call_id": fc["call_id"],
                "output": result,
            })

        print(f"   [TOOL RESULT] Sending results back...")
        print(f"   Agent: ", end="", flush=True)

        # Continue with streaming after function call
        stream4 = openai_client.responses.create(
            extra_body={
                "agent_reference": {
                    "name": agent_fn.name,
                    "version": agent_fn.version,
                    "type": "agent_reference",
                }
            },
            input=tool_outputs,
            previous_response_id=response_id,
            stream=True,
        )

        for event in stream4:
            event_type = event.type if hasattr(event, "type") else type(event).__name__
            if event_type == "response.output_text.delta":
                print(event.delta, end="", flush=True)

        print()  # newline

    # -- Step 4: Streaming vs Blocking Comparison -----------
    print_step("Step 4: Time-to-First-Token — Streaming vs Blocking")

    comparison_query = (
        "Explain the difference between comprehensive and "
        "collision auto insurance coverage in 2 sentences."
    )
    print(f"   Query: \"{comparison_query[:60]}...\"")
    print()

    # Blocking (non-streaming)
    t0 = time.time()
    blocking_resp = openai_client.responses.create(
        extra_body={
            "agent_reference": {
                "name": agent.name,
                "version": agent.version,
                "type": "agent_reference",
            }
        },
        input=comparison_query,
    )
    blocking_time = time.time() - t0
    blocking_text = blocking_resp.output_text

    # Streaming
    t0 = time.time()
    streaming_first_token = None
    streaming_text = ""

    stream5 = openai_client.responses.create(
        extra_body={
            "agent_reference": {
                "name": agent.name,
                "version": agent.version,
                "type": "agent_reference",
            }
        },
        input=comparison_query,
        stream=True,
    )

    for event in stream5:
        event_type = event.type if hasattr(event, "type") else type(event).__name__
        if event_type == "response.output_text.delta":
            if streaming_first_token is None:
                streaming_first_token = time.time() - t0
            streaming_text += event.delta

    streaming_total = time.time() - t0

    print(f"   | Metric                 | Blocking     | Streaming    |")
    print(f"   |------------------------|--------------|--------------|")
    print(f"   | Time to first token    | {blocking_time:.2f}s (full) | {streaming_first_token:.2f}s        |")
    print(f"   | Total response time    | {blocking_time:.2f}s        | {streaming_total:.2f}s        |")
    print(f"   | Response length        | {len(blocking_text):>5d} chars | {len(streaming_text):>5d} chars |")
    print()
    print("   Streaming delivers first token faster → better perceived UX")
    print("   Users see content immediately instead of waiting for full response")

    # -- Step 5: Clean Up -----------------------------------
    print_step("Step 5: Clean Up")

    for name in ["smartclaims-stream", "smartclaims-stream-fn"]:
        try:
            project_client.agents.delete(name)
            print(f"   [OK] Deleted: {name}")
        except Exception:
            print(f"   [SKIP] {name}")

    print(f"\n{'='*65}")
    print("  [OK] Lab 9 Complete!")
    print("  Next: python labs/lab10_azure_ai_search.py")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
