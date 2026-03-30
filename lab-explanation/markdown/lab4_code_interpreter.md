# Lab 4: Code Interpreter Agent -- Claims Analytics

## What It Does
Uploads claims CSV into a sandboxed Python environment where the agent writes and executes code (pandas, matplotlib) to analyze data and generate charts.

## Flow

```
  contoso_claims_data.csv
    |
    v
  files.create(purpose="assistants") -- upload CSV to platform
    |
    v
  CodeInterpreterTool + CodeInterpreterContainerAuto(file_ids=[...])
    |
    v
  Create agent with Code Interpreter attached
    |
    v
  User asks: "Executive summary of claims data"
    |
    v
  Agent writes Python code internally:
      import pandas as pd
      df = pd.read_csv(...)
      df.groupby('status').count()
    |
    v
  Returns analysis results + optional PNG charts
    |
    v
  Download charts to outputs/ folder
```

## Key Concepts

- **Code Interpreter** -- sandboxed Python with pandas/matplotlib pre-installed
- **CodeInterpreterContainerAuto** -- pre-loads your CSV into the sandbox
- The agent WRITES and EXECUTES Python code -- you never see it unless you inspect
- Charts are generated as PNG files inside the container
- Use `containers.files.content.retrieve()` to download generated files

## SDK Used

- `openai_client.files.create(purpose="assistants", file)`
- `CodeInterpreterTool(container=CodeInterpreterContainerAuto(file_ids=[...]))`
- `openai_client.containers.files.content.retrieve(container_id, file_id)`
