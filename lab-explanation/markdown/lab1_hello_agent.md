# Lab 1: Your First Agent -- Hello World

## What It Does
Creates your first AI agent with custom instructions and demonstrates single-turn and multi-turn conversations.

## Flow

```
  Define agent instructions (system prompt)
    |
    v
  project_client.agents.create_version("smartclaims-hello")
    |
    v
  Single request -----> agent responds with personality
    |
    v
  Create conversation (stateful session)
    |
    v
  Turn 1: "File a claim for car accident"  --> agent responds
    |
    v
  Turn 2: "What documents do I need?"      --> agent remembers context
    |
    v
  Delete agent (cleanup)
```

## Key Concepts

- **PromptAgentDefinition** -- defines the agent's model and system instructions
- **create_version()** -- registers the agent in your Foundry project
- **agent_reference** -- routes your request to YOUR agent (not the raw model)
- **conversations.create()** -- starts a stateful session so the agent remembers context
- **conversation ID** -- pass it in each call to maintain multi-turn memory

## SDK Used

- `PromptAgentDefinition(model, instructions)`
- `project_client.agents.create_version(agent_name, definition)`
- `openai_client.responses.create(extra_body={"agent_reference": {...}}, input=...)`
- `openai_client.conversations.create()`
