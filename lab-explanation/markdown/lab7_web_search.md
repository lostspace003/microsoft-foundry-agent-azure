# Lab 7: Tavily Web Search -- Regulatory Intelligence

## What It Does
Adds live web search capability using Tavily API, wrapped as a custom function tool. The agent can now search the internet for current regulations and news.

## Flow

```
  TAVILY_API_KEY from .env
    |
    v
  Define web_search(query) function
    |
    v
  Register as function tool schema
    |
    v
  Create regulatory intelligence agent
    |
    v
  User asks: "Latest insurance regulatory changes in the US?"
    |
    v
  Agent calls web_search(query="...")
    |
    v
  YOUR CODE calls Tavily API --> returns search results + answer
    |
    v
  Send results back to agent
    |
    v
  Agent summarizes findings with source URLs
```

## Key Concepts

- **Web search as function tool** -- same pattern as Lab 5, different function
- **Tavily API** -- search engine optimized for AI agents (includes pre-made answers)
- **Real-time data** -- agent can access current information beyond its training data
- **Source citations** -- agent includes URLs from search results
- Requires `TAVILY_API_KEY` in `.env` (free tier: 1000 calls/month)

## SDK Used

- Same function tool pattern as Lab 5
- `TavilyClient(api_key).search(query, max_results=5, include_answer=True)`
- `ask_with_functions()` handles the call loop
