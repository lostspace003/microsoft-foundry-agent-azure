# Lab 6: Multi-Tool Agent -- Complete SmartClaims

## What It Does
Combines all three tool types (File Search + Code Interpreter + Custom Functions) into a single unified agent that picks the right tool for each question.

## Flow

```
  Upload CSV ---------> Code Interpreter (analytics)
  Index policy doc ---> File Search (RAG / Q&A)
  Register functions --> Custom Functions (claim lookup, fraud)
    |
    |   All three combined into one tools list
    v
  Create unified agent with ALL tools
    |
    v
  "What is the status of CLM-0042?"     --> Function Tool
  "Does our policy cover ride-sharing?"  --> File Search
  "Show claims by status breakdown"      --> Code Interpreter
  "Fraud risk for $350K fire claim?"     --> Function Tool
  "Highest avg amount + policy exclusions?" --> Code Interpreter + File Search
```

## Key Concepts

- **Tool selection** -- the agent automatically picks the right tool per query
- **Tool chaining** -- agent can use multiple tools in a single response
- **Native tools** (File Search, Code Interpreter) run server-side
- **Custom functions** run client-side with the function call loop
- All tools are passed as a single list to `PromptAgentDefinition`

## SDK Used

- Code Interpreter as plain dict: `{"type": "code_interpreter", "container": {...}}`
- File Search as plain dict: `{"type": "file_search", "vector_store_ids": [...]}`
- Function schemas as plain dicts: `{"type": "function", ...}`
- `ask_with_functions()` handles the mixed tool execution loop
