# Lab 3: File Search Agent -- Policy Q&A (RAG)

## What It Does
Uploads a policy document, indexes it in a vector store, and creates an agent that answers questions by searching the document.

## Flow

```
  contoso_insurance_policy.md
    |
    v
  Create Vector Store ("ContosoPolicyStore")
    |
    v
  upload_and_poll() -- chunks, embeds, and indexes the document
    |
    v
  FileSearchTool(vector_store_ids=[...])
    |
    v
  Create agent with FileSearchTool attached
    |
    v
  User asks: "What is the max auto liability coverage?"
    |
    v
  Agent automatically searches the vector store
    |
    v
  Returns answer with citations from the policy document
```

## Key Concepts

- **RAG (Retrieval-Augmented Generation)** -- agent searches documents before answering
- **Vector Store** -- managed index that handles chunking and embedding for you
- **upload_and_poll()** -- uploads, processes, and waits until indexing is complete
- **FileSearchTool** -- connects the agent to the vector store
- Agent answers ONLY from the document, not from general knowledge

## SDK Used

- `openai_client.vector_stores.create(name)`
- `openai_client.vector_stores.files.upload_and_poll(vector_store_id, file)`
- `FileSearchTool(vector_store_ids=[...])`
- `PromptAgentDefinition(model, instructions, tools=[file_search_tool])`
