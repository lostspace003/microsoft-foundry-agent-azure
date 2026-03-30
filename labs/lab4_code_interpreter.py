"""
Lab 4: Code Interpreter Agent — Claims Analytics
=================================================
Run: python labs/lab4_code_interpreter.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import (
    get_clients, MODEL, CLAIMS_CSV, OUTPUTS_DIR,
    print_header, print_step,
)
from azure.ai.projects.models import (
    PromptAgentDefinition,
    CodeInterpreterTool,
    CodeInterpreterContainerAuto,
)


def main():
    print_header(4, "Code Interpreter Agent — Claims Analytics")
    project_client, openai_client = get_clients()

    # ── Step 1: Upload claims CSV ───────────────────────
    # purpose="assistants" tells the service this file is
    # for agent use in a sandbox environment.
    print_step("Step 1: Upload Claims CSV")

    file = openai_client.files.create(
        purpose="assistants",
        file=open(str(CLAIMS_CSV), "rb"),
    )
    print(f"   File uploaded: {file.id}")

    # ── Step 2: Configure Code Interpreter ──────────────
    # CodeInterpreterContainerAuto creates a Python sandbox
    # with your CSV pre-loaded. The agent can read this
    # file inside its sandbox using pandas.
    print_step("Step 2: Configure Code Interpreter")

    code_interpreter = CodeInterpreterTool(
        container=CodeInterpreterContainerAuto(file_ids=[file.id])
    )
    print("   ✅ Sandbox configured with claims CSV")

    # ── Step 3: Create analytics agent ──────────────────
    print_step("Step 3: Create Analytics Agent")

    agent = project_client.agents.create_version(
        agent_name="smartclaims-analytics",
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=(
                "You are SmartClaims Analytics Agent for Contoso Insurance. "
                "You have a claims CSV dataset. Columns: claim_id, "
                "policy_number, policyholder_name, claim_date, incident_date, "
                "incident_type, claim_amount, approved_amount, status, "
                "adjuster_name, fraud_flag, fraud_score, region, policy_type, "
                "deductible, settlement_date, processing_days. "
                "Use pandas for analysis and matplotlib for charts. "
                "When creating charts, always save them as PNG files. "
                "Provide executive-summary style insights with numbers."
            ),
            tools=[code_interpreter],
        ),
    )
    print(f"   Agent: {agent.name} v{agent.version}")

    # ── Step 4: Run analytics ───────────────────────────
    print_step("Step 4: Run Analytics Queries")

    conversation = openai_client.conversations.create()

    def ask(q):
        return openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent_reference": {
                "name": agent.name, "version": agent.version,
                "type": "agent_reference"}},
            input=q,
        )

    queries = [
        "Load the CSV. Give an executive summary: total claims, "
        "total amount, average amount, status distribution.",

        "Create a bar chart of claims count by incident type. "
        "Use professional colors. Save the chart as a PNG file.",

        "Analyze fraud: what % are flagged? Break down fraud "
        "rates by region and by incident type.",

        "Average processing days by status and region. "
        "Which region resolves claims fastest?",

        "Top 10 highest claims — show claim ID, type, amount, "
        "status, and fraud score.",
    ]

    responses = []
    for i, q in enumerate(queries, 1):
        print(f"\n   ┌─ Analysis {i}: {q[:70]}...")
        r = ask(q)
        responses.append(r)
        out = r.output_text
        print(f"   └─ 📊 {out}")

    # ── Step 5: Download charts (if available) ──────────
    print_step("Step 5: Check for Generated Charts")
    chart_count = 0
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    for resp in responses:
        try:
            for item in resp.output:
                if not hasattr(item, "content"):
                    continue
                for block in item.content:
                    # Handle image blocks directly
                    if hasattr(block, "type") and block.type == "image":
                        if hasattr(block, "image") and hasattr(block.image, "file_id"):
                            fid = block.image.file_id
                            cid = getattr(block.image, "container_id", None)
                            chart_count += 1
                            fname = f"chart_{chart_count}_{fid}.png"
                            print(f"   📥 Chart found: {fid}")
                            if cid:
                                content = openai_client.containers.files.content.retrieve(
                                    container_id=cid, file_id=fid,
                                )
                                path = OUTPUTS_DIR / fname
                                with open(str(path), "wb") as f:
                                    f.write(content.read())
                                print(f"   ✅ Saved: {path.name}")

                    # Handle annotations on text blocks
                    if hasattr(block, "annotations"):
                        for ann in block.annotations:
                            if hasattr(ann, "container_id") and hasattr(ann, "file_id"):
                                chart_count += 1
                                fname = f"chart_{chart_count}_{ann.file_id}.png"
                                print(f"   📥 Chart found: {ann.file_id}")
                                content = openai_client.containers.files.content.retrieve(
                                    container_id=ann.container_id,
                                    file_id=ann.file_id,
                                )
                                path = OUTPUTS_DIR / fname
                                with open(str(path), "wb") as f:
                                    f.write(content.read())
                                print(f"   ✅ Saved: {path.name}")
        except Exception as e:
            print(f"   ℹ️  Error extracting chart: {e}")

    if chart_count == 0:
        print("   ℹ️  No downloadable charts found in responses.")
        print("   💡 Charts may have been rendered inline in the sandbox.")

    # ── Step 6: Clean up ────────────────────────────────
    print_step("Step 6: Clean Up")
    project_client.agents.delete(agent.name)
    print("   ✅ Agent deleted")

    print(f"\n{'='*65}")
    print("  ✅ Lab 4 Complete!")
    if chart_count > 0:
        print(f"  📊 {chart_count} chart(s) saved to: {OUTPUTS_DIR}")
    print("  Next → python labs/lab5_function_tools.py")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
