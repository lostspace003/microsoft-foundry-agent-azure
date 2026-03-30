# Lab 10: Azure AI Search Grounding -- Enterprise Knowledge Base

## What It Does
Creates a search index, populates it with chunked policy documents, and connects the agent to it for production-grade RAG. This is the enterprise upgrade to Lab 3's managed FileSearchTool.

## Flow

```
  Resolve Foundry connection (endpoint + API key)
    |
    v
  Create search index schema (id, title, content, category)
    |
    v
  Chunk contoso_insurance_policy.md by ## headings
    |   Auto-categorize: claims, fraud, coverage, exclusions, etc.
    |
    v
  Upload chunked documents to index
    |
    v
  AzureAISearchTool(connection_id, index_name, query_type)
    |
    v
  Create agent with AI Search tool
    |
    v
  User asks: "What are our fraud investigation procedures?"
    |
    v
  Agent searches YOUR enterprise index automatically
    |
    v
  Returns grounded answer from your knowledge base
    |
    v
  Clean up: delete agent + index

  Lab 3 (FileSearch)          vs     Lab 10 (AI Search)
  -------------------                -------------------
  Upload files to platform           Create + populate your own index
  Platform manages index             You control the index
  Vector search only                 Hybrid search (vector+keyword)
  Small doc sets                     Millions of documents
  No security trimming               Per-document ACLs
  Great for prototyping              Great for production
```

## Key Concepts

- **Azure AI Search** -- enterprise search service with hybrid search, semantic ranking
- **Programmatic index creation** -- create index schema and upload documents from code
- **Document chunking** -- split Markdown by headings with auto-categorization
- **Foundry connections** -- retrieve endpoint + API key from project connections (no hardcoded keys)
- **Hybrid search** -- combines vector similarity + keyword matching for better results
- **Security trimming** -- per-document access control (who can see what)
- **Platform-managed search** -- no function call loop, agent searches automatically

## SDK Used

- `project_client.connections.get(name, include_credentials=True)` -- resolve connection
- `SearchIndexClient` + `SearchClient` from `azure-search-documents`
- `AzureAISearchTool(azure_ai_search=AzureAISearchToolResource(...))`
- `AISearchIndexResource(project_connection_id, index_name, query_type)`
- `AzureAISearchQueryType.SIMPLE` -- keyword search (also supports SEMANTIC, VECTOR)
- Requires: AI Search resource + Foundry project connection + `.env` vars
