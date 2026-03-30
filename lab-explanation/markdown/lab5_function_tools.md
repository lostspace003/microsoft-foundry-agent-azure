# Lab 5: Function Tool Agent -- Custom Business Logic

## What It Does
Adds custom business functions (claim lookup, fraud scoring) as tools the agent can call. YOU execute the functions locally and send results back.

## Flow

```
  Define function schemas (JSON)
    |
    v
  Register get_claim_status() and calculate_fraud_risk()
    |
    v
  Create agent with function tool schemas attached
    |
    v
  User asks: "What is the status of claim CLM-0042?"
    |
    v
  Agent decides to call get_claim_status(claim_id="CLM-0042")
    |
    v
  YOUR CODE executes the function locally (reads CSV)
    |
    v
  Send function result back to agent
    |
    v
  Agent formats the result into a natural language answer
```

## Key Concepts

- **Function Tools** -- agent decides WHEN to call, YOU execute the code
- **Function call loop** -- agent may call multiple functions before answering
- **Schema** -- JSON Schema defines parameters (types, enums, required fields)
- **Client-side execution** -- functions run in YOUR environment, not the cloud
- **ask_with_functions()** -- utility that handles the call-execute-respond loop

## SDK Used

- Function schemas as plain dicts: `{"type": "function", "name": "...", "parameters": {...}}`
- `response.output` items with `type == "function_call"` -- agent's tool call request
- `previous_response_id` -- sends function results back for follow-up
