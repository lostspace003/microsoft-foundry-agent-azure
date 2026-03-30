# Lab 9: Streaming Responses -- Real-Time Agent UX

## What It Does
Switches from blocking (wait-for-full-response) to streaming (token-by-token) output. Shows how to handle stream events and streaming with function tools.

## Flow

```
  Create agent
    |
    v
  responses.create(..., stream=True)
    |
    v
  Event stream arrives token by token:
    |
    |   ResponseCreatedEvent -------> "Response started"
    |   ResponseTextDeltaEvent -----> "Compre"
    |   ResponseTextDeltaEvent -----> "hensive"
    |   ResponseTextDeltaEvent -----> " auto"
    |   ResponseTextDeltaEvent -----> " insurance..."
    |   ResponseTextDoneEvent ------> "Full text complete"
    |   ResponseCompletedEvent -----> "Done"
    |
    v
  Streaming with function tools:
    |
    |   Stream starts
    |   FunctionCallArgumentsDelta --> building arguments
    |   FunctionCallArgumentsDone ---> execute function locally
    |   Send results back
    |   Stream resumes with answer
    |
    v
  Compare: Time-to-first-token (streaming) vs full wait (blocking)
```

## Key Concepts

- **stream=True** -- single parameter change, completely different UX
- **Time-to-first-token** -- user sees content in ~0.3s instead of waiting ~2s
- **Event types** -- delta (partial), done (complete), created/completed (lifecycle)
- **Function calls in stream** -- detect tool calls mid-stream, execute, resume
- **flush=True** -- Python print trick to show tokens as they arrive

## SDK Used

- `openai_client.responses.create(..., stream=True)` -- returns event iterator
- `event.type == "response.output_text.delta"` -- partial text
- `event.type == "response.function_call_arguments.done"` -- function call ready
- `event.delta` -- the text fragment
