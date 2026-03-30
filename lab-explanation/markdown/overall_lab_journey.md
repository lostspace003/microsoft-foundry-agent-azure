# SmartClaims Agent -- Complete Lab Journey

## Diagram Files

| File | Lab | Topic |
|------|-----|-------|
| [lab0_test_connection.svg](../visuals/lab0_test_connection.svg) | Lab 0 | Verify .env, credentials, basic model call |
| [lab1_hello_agent.svg](../visuals/lab1_hello_agent.svg) | Lab 1 | Create agent, single-turn + multi-turn |
| [lab3_file_search_rag.svg](../visuals/lab3_file_search_rag.svg) | Lab 3 | Vector store + policy Q&A |
| [lab4_code_interpreter.svg](../visuals/lab4_code_interpreter.svg) | Lab 4 | Sandbox Python + CSV analytics |
| [lab5_function_tools.svg](../visuals/lab5_function_tools.svg) | Lab 5 | Custom business logic (claim lookup, fraud) |
| [lab6_multi_tool_agent.svg](../visuals/lab6_multi_tool_agent.svg) | Lab 6 | File Search + Code Interpreter + Functions |
| [lab7_web_search.svg](../visuals/lab7_web_search.svg) | Lab 7 | Tavily live web search |
| [lab8_observability.svg](../visuals/lab8_observability.svg) | Lab 8 | Tracing, metrics, monitoring in Foundry |
| [lab9_streaming_responses.svg](../visuals/lab9_streaming_responses.svg) | Lab 9 | Token-by-token output with function calls |
| [lab10_azure_ai_search.svg](../visuals/lab10_azure_ai_search.svg) | Lab 10 | Enterprise RAG with existing search indexes |
| [lab11_fastapi_deployment.svg](../visuals/lab11_fastapi_deployment.svg) | Lab 11 | FastAPI web app + Azure App Service |
| [lab12_container_app_deployment.md](lab12_container_app_deployment.md) | Lab 12 | Container App + Observability + Managed Identity |
| [overall_lab_journey.svg](../visuals/overall_lab_journey.svg) | All | Full progression, phases, tool types |

## Overall Architecture

```
                        SmartClaims AI Agent
                    Microsoft Foundry Agent Service

  YOUR CODE                    FOUNDRY PLATFORM                AZURE SERVICES
  ----------                   ----------------                --------------
  Python scripts               Agent orchestration            Azure OpenAI (gpt-4o-mini)
  FastAPI web app               Tool execution                 Azure AI Search
  Dockerfile                    Conversation state             Azure Container Apps
  Function tools                Vector stores                  Azure Container Registry
  Business logic                OpenTelemetry                  Azure Monitor
```

## Lab Progression

```
  Lab 0: Test Connection
    |   Verify .env, credentials, basic model call
    |
    v
  Lab 1: Hello Agent
    |   Create agent, single-turn, multi-turn conversations
    |
    v
  Lab 3: File Search (RAG)                Lab 4: Code Interpreter
    |   Vector store + policy Q&A            |   Sandbox Python + CSV analytics
    |                                        |
    v                                        v
  Lab 5: Function Tools
    |   Custom business logic (claim lookup, fraud scoring)
    |
    v
  Lab 6: Multi-Tool Agent
    |   Combine: File Search + Code Interpreter + Functions
    |   Agent picks the right tool automatically
    |
    v
  Lab 7: Tavily Web Search
    |   Live web search as function tool (regulatory intelligence)
    |
    v
  Lab 8: Deep Observability
    |   Tracing, metrics, monitoring with OpenTelemetry + Azure Monitor
    |
    v
  Lab 9: Streaming Responses
    |   Token-by-token output, streaming with function calls
    |
    v
  Lab 10: Azure AI Search Grounding
    |   Enterprise RAG with existing search indexes
    |
    v
  Lab 11: FastAPI Web App Deployment
    |   Wrap everything into a web app, local + App Service
    |
    v
  Lab 12: Container App Deployment
      Dockerfile + ACR + Container App + Observability + Managed Identity
      Production deployment with scale-to-zero and passwordless auth
```

## Tool Types Across Labs

```
  TOOL TYPE             LABS      HOW IT WORKS
  ---------             ----      ------------

  File Search (RAG)     3, 6      Platform uploads, chunks, embeds, searches
                                  Agent queries vector store automatically

  Code Interpreter      4, 6      Platform runs Python in sandbox
                                  Agent writes pandas/matplotlib code

  Custom Functions      5, 6, 7   YOU define schema + implement function
                                  Agent calls it, YOU execute, send results back

  Observability         8         OpenTelemetry traces + custom metrics
                                  Azure Monitor, KQL queries, alerting

  Azure AI Search       10        Platform searches YOUR existing index
                                  Hybrid search, security trimming, no upload

  Streaming             9         Platform sends tokens as they generate
                                  YOUR code processes event stream

  Container Deploy      12        Dockerfile + ACR cloud build
                                  Container App with Managed Identity
                                  Integrated observability (traces + metrics)
```

## Data Flow

```
  contoso_insurance_policy.md ----> Vector Store (Lab 3)
                                      |
                                      v
                                  File Search Tool ---> Agent answers policy questions

  contoso_claims_data.csv --------> Code Interpreter sandbox (Lab 4)
                                      |
                                      v
                                  Agent runs pandas ---> Analytics + charts

  contoso_claims_data.csv --------> get_claim_status() function (Lab 5)
                                      |
                                      v
                                  Agent calls function ---> Claim lookup results

  All agent calls -----------------> OpenTelemetry (Lab 8)
                                      |
                                      v
                                  Traces + Metrics ---> Azure Monitor dashboards

  Azure AI Search index ----------> AI Search Tool (Lab 10)
                                      |
                                      v
                                  Agent searches index ---> Enterprise knowledge

  All of the above ----------------> Dockerfile + ACR (Lab 12)
                                      |
                                      v
                                  Container App ---> Production deployment
                                      |               (Managed Identity, HTTPS,
                                      |                scale-to-zero, health checks)
                                      v
                                  OpenTelemetry ---> Azure Monitor dashboards
```

## Prerequisites by Lab

```
  Lab    Requires
  ---    --------
  0-1    .env (PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME), az login
  3-6    Same as above (data files included in data/ folder)
  7      + TAVILY_API_KEY
  8-9    Same as Labs 0-6
  10     + AI_SEARCH_CONNECTION_NAME, AI_SEARCH_INDEX_NAME
  11     + Azure CLI, Azure subscription (for App Service deployment)
  12     + Azure CLI, Dockerfile, ACR (for Container App deployment)
```

## Key SDK Patterns

```
  Pattern 1: Create and use an agent
  ----------------------------------
  agent = project_client.agents.create_version(agent_name, definition)
  response = openai_client.responses.create(
      extra_body={"agent_reference": {"name": ..., "version": ..., "type": "agent_reference"}},
      input="user message"
  )

  Pattern 2: Function call loop
  -----------------------------
  response = openai_client.responses.create(...)
  for fc in response.output:          # check for function_call items
      result = my_function(fc.args)   # execute locally
      send result back via previous_response_id

  Pattern 3: Streaming
  --------------------
  stream = openai_client.responses.create(..., stream=True)
  for event in stream:
      if event.type == "response.output_text.delta":
          print(event.delta, end="", flush=True)

  Pattern 4: Cleanup
  ------------------
  project_client.agents.delete(agent_name)
  openai_client.vector_stores.delete(vector_store_id)
```
