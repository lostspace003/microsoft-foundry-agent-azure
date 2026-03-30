"""
Lab 10: Azure AI Search Grounding — Enterprise Knowledge Base
==============================================================
Create a search index, populate it with policy documents,
and connect agents to it for production-grade RAG.
Run: python labs/lab10_azure_ai_search.py
"""

import sys
import os
import re
import hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import (
    get_clients, MODEL, print_header, print_step,
    POLICY_DOC,
)
from azure.ai.projects.models import (
    PromptAgentDefinition,
    AzureAISearchTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
)
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
)


# --------------------------------------------------
# Helper: Chunk a Markdown document by ## headings
# --------------------------------------------------
def chunk_policy_document(filepath):
    """
    Split a Markdown policy document into chunks by ## sections.
    Each chunk gets an id, title, content, and category.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    sections = re.split(r"\n(?=## )", text)

    chunks = []
    for section in sections:
        section = section.strip()
        if not section or len(section) < 20:
            continue

        lines = section.split("\n", 1)
        title = lines[0].lstrip("#").strip()
        content = section

        # Auto-categorize based on title keywords
        title_lower = title.lower()
        category = "policy"
        for keyword, cat in [
            ("claim", "claims"), ("fraud", "fraud"),
            ("exclu", "exclusions"), ("deduct", "deductibles"),
            ("coverage", "coverage"), ("renewal", "renewal"),
            ("cancel", "renewal"), ("contact", "contact"),
        ]:
            if keyword in title_lower:
                category = cat
                break

        doc_id = hashlib.md5(title.encode()).hexdigest()[:16]
        chunks.append({
            "id": doc_id,
            "title": title,
            "content": content,
            "category": category,
        })

    return chunks


def main():
    print_header(10, "Azure AI Search Grounding — Enterprise Knowledge Base")

    # -- Step 1: Architecture Comparison --------------------
    print_step("Step 1: FileSearch (Lab 3) vs Azure AI Search (Lab 10)")
    print()
    print("   Lab 3 — FileSearchTool (Managed Vector Store):")
    print("   ┌───────────────────────────────────────────────┐")
    print("   │  Upload files → Platform chunks & embeds      │")
    print("   │  → Managed vector store → Agent queries it    │")
    print("   │  Great for: quick prototyping, small doc sets  │")
    print("   └───────────────────────────────────────────────┘")
    print()
    print("   Lab 10 — AzureAISearchAgentTool (Your Index):")
    print("   ┌───────────────────────────────────────────────┐")
    print("   │  Your Azure AI Search index (already exists)  │")
    print("   │  → Agent connects via Foundry connection      │")
    print("   │  → Hybrid search (vector + keyword + semantic)│")
    print("   │  Great for: production, large doc sets,       │")
    print("   │  security trimming, custom analyzers          │")
    print("   └───────────────────────────────────────────────┘")

    # -- Step 2: Validate Configuration ---------------------
    print_step("Step 2: Validate Azure AI Search Configuration")

    connection_name = os.environ.get("AI_SEARCH_CONNECTION_NAME", "")
    index_name = os.environ.get("AI_SEARCH_INDEX_NAME", "contoso-insurance-index")

    if not connection_name:
        print("   [ERROR] AI_SEARCH_CONNECTION_NAME not set in .env")
        print("   Required:")
        print("     AI_SEARCH_CONNECTION_NAME=<your-connection-name>")
        print("     AI_SEARCH_INDEX_NAME=<your-index-name>")
        return

    project_client, openai_client = get_clients()

    # Resolve search endpoint + API key from Foundry connection
    print(f"   [OK] Connection:  {connection_name}")
    azs_connection = project_client.connections.get(connection_name)
    connection_id = azs_connection.id
    search_endpoint = azs_connection.target
    print(f"   [OK] Endpoint:    {search_endpoint}")

    azs_with_secrets = project_client.connections.get(
        connection_name, include_credentials=True
    )
    api_key = azs_with_secrets.credentials.api_key
    credential = AzureKeyCredential(api_key)
    print(f"   [OK] API key:     Retrieved from Foundry connection")
    print(f"   [OK] Index:       {index_name}")

    # -- Step 3: Create Search Index -----------------------
    print_step("Step 3: Create Search Index Schema")

    index_client = SearchIndexClient(
        endpoint=search_endpoint, credential=credential
    )

    fields = [
        SimpleField(
            name="id", type=SearchFieldDataType.String,
            key=True, filterable=True,
        ),
        SearchableField(
            name="title", type=SearchFieldDataType.String,
            filterable=True, sortable=True,
        ),
        SearchableField(
            name="content", type=SearchFieldDataType.String,
        ),
        SearchableField(
            name="category", type=SearchFieldDataType.String,
            filterable=True, facetable=True,
        ),
    ]

    index = SearchIndex(name=index_name, fields=fields)
    result = index_client.create_or_update_index(index)
    print(f"   [OK] Index '{result.name}' created/updated")
    print(f"        Fields: {[f.name for f in result.fields]}")

    # -- Step 4: Chunk & Upload Policy Document ------------
    print_step("Step 4: Chunk & Upload Policy Document")

    if not POLICY_DOC.exists():
        print(f"   [ERROR] Policy document not found: {POLICY_DOC}")
        print("   Run Lab 2 first to generate the data files.")
        return

    chunks = chunk_policy_document(POLICY_DOC)
    print(f"   [OK] Chunked policy document into {len(chunks)} sections")

    for c in chunks:
        print(f"        - [{c['category']:12s}] {c['title'][:60]}")

    search_client = SearchClient(
        endpoint=search_endpoint,
        index_name=index_name,
        credential=credential,
    )

    upload_result = search_client.upload_documents(documents=chunks)
    succeeded = sum(1 for r in upload_result if r.succeeded)
    print(f"   [OK] Uploaded {succeeded}/{len(chunks)} documents to index")

    # -- Step 5: Create Search-Grounded Agent ---------------
    print_step("Step 5: Create Azure AI Search Grounded Agent")

    search_tool = AzureAISearchTool(
        azure_ai_search=AzureAISearchToolResource(
            indexes=[
                AISearchIndexResource(
                    project_connection_id=connection_id,
                    index_name=index_name,
                    query_type=AzureAISearchQueryType.SIMPLE,
                ),
            ]
        )
    )

    agent = project_client.agents.create_version(
        agent_name="smartclaims-search",
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=(
                "You are SmartClaims Knowledge Agent. You have access to "
                "the company's enterprise knowledge base via Azure AI Search. "
                "Use it to answer questions about insurance policies, claims "
                "procedures, precedents, and guidelines. Always cite the "
                "source documents when providing information. If you cannot "
                "find relevant information in the knowledge base, say so."
            ),
            tools=[search_tool],
        ),
    )
    print(f"   Agent: {agent.name} v{agent.version}")
    print(f"   Index: {index_name}")
    print(f"   Query: SIMPLE (keyword search)")

    # -- Step 6: Enterprise Knowledge Queries ---------------
    print_step("Step 6: Enterprise Knowledge Queries")

    queries = [
        (
            "Claims Procedures",
            "What is the standard procedure for filing an insurance claim? "
            "What documentation is required?"
        ),
        (
            "Policy Coverage",
            "What types of coverage are available under the comprehensive "
            "insurance policy? List all covered scenarios."
        ),
        (
            "Fraud Policy",
            "What are the fraud detection mechanisms and consequences "
            "for fraudulent claims?"
        ),
    ]

    for title, question in queries:
        print(f"\n   --- {title} ---")
        print(f"   User: {question[:80]}")

        response = openai_client.responses.create(
            extra_body={
                "agent_reference": {
                    "name": agent.name,
                    "version": agent.version,
                    "type": "agent_reference",
                }
            },
            input=question,
        )

        answer = response.output_text
        if len(answer) > 500:
            answer = answer[:500] + "..."
        print(f"   Agent: {answer}")

    # -- Step 7: Compare RAG Approaches ---------------------
    print_step("Step 7: FileSearch vs Azure AI Search Comparison")
    print()
    print("   | Feature              | Lab 3 (FileSearch)     | Lab 10 (AI Search)       |")
    print("   |----------------------|------------------------|--------------------------|")
    print("   | Document scale       | Small (< 100 files)    | Large (millions of docs)  |")
    print("   | Search type          | Vector only            | Hybrid (vector+keyword)   |")
    print("   | Index management     | Managed by platform    | You control the index     |")
    print("   | Security trimming    | Not supported          | Supported (per-doc ACLs)  |")
    print("   | Custom analyzers     | No                     | Yes (language, phonetic)  |")
    print("   | Existing index       | Must re-upload         | Connect to existing       |")
    print("   | Scoring profiles     | No                     | Yes (boost/penalize)      |")
    print("   | Semantic ranking     | No                     | Yes (with semantic config)|")
    print("   | Setup effort         | Minimal (just upload)  | Moderate (index + connect)|")
    print("   | Best for             | Prototyping, demos     | Production, enterprise    |")

    # -- Step 8: Clean Up -----------------------------------
    print_step("Step 8: Clean Up")

    project_client.agents.delete(agent.name)
    print("   [OK] Agent deleted")

    index_client.delete_index(index_name)
    print(f"   [OK] Index '{index_name}' deleted")

    print(f"\n{'='*65}")
    print("  [OK] Lab 10 Complete!")
    print("  Next: python labs/lab11_fastapi_webapp.py")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
