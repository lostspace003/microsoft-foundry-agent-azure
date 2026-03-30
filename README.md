# SmartClaims AI Agent

### AI-Powered Insurance Claims Assistant — Microsoft Foundry & Azure AI

SmartClaims is a production-grade AI agent that automates insurance workflows using **Microsoft Foundry Agent Service**, **Azure OpenAI (GPT-4o-mini)**, and **FastAPI**. It combines policy Q&A, claims analytics, fraud detection, web-based regulatory intelligence, and full observability into a single deployable application.

The project is structured as **11 progressive labs** — each one introduces a new capability, building from a basic API connection test to a fully containerized, observable web application deployed on Azure Container Apps.

---

## Architecture

The system is composed of the following layers:

**Your Code** — Python scripts, FastAPI app, Dockerfile, custom business functions

**Foundry Platform** — Agent orchestration, tool execution, conversation state, vector stores, OpenTelemetry tracing

**Azure Services** — Azure OpenAI (GPT-4o-mini), Azure AI Search, Azure Container Apps, Azure Container Registry, Azure Monitor

All agent interactions go through the **Microsoft Foundry Agent Service**, which manages tool routing, conversation state, and model inference. The Foundry SDK (v2.x) uses an OpenAI-compatible API surface with `agent_reference` routing.

---

## What It Can Do

**Policy Q&A (RAG)** — Upload the Contoso insurance policy document into a vector store. The agent retrieves relevant sections and answers questions grounded in the actual policy text, with citations.

**Claims Analytics** — Upload a 500-record claims CSV into a sandboxed Code Interpreter. The agent writes and executes pandas/matplotlib code to produce executive summaries, breakdowns by status/region/type, and charts.

**Claim Lookup & Fraud Scoring** — Custom function tools let the agent look up individual claims by ID and calculate fraud risk scores. These run client-side — the agent decides when to call them, your code executes the logic.

**Regulatory Intelligence** — A Tavily-powered web search tool lets the agent fetch real-time regulatory updates and insurance news, with source URLs.

**Multi-Tool Orchestration** — A unified agent combines all tools (File Search + Code Interpreter + Functions). It automatically picks the right tool for each question and can chain tools in a single response.

**Streaming** — Token-by-token output with function call handling for responsive UX.

**Observability** — OpenTelemetry tracing and custom metrics (latency, token usage, error rates) with Azure Monitor integration and KQL dashboards.

**Production Deployment** — Dockerfile, Azure Container Registry, Azure Container Apps with Managed Identity, scale-to-zero, HTTPS, and health checks.

---

## Project Structure

```
smart-claims-agent-project/
│
├── app/                          # FastAPI web application
│   ├── main.py                   # Routes: chat, policy-qa, analytics, claim-lookup, fraud-risk
│   ├── agent_service.py          # Agent lifecycle, tool orchestration, instrumented with OTel
│   ├── observability.py          # OpenTelemetry setup (Azure Monitor or console)
│   └── templates/
│       └── index.html            # Frontend UI (tabbed interface + Chart.js)
│
├── labs/                         # Standalone Python scripts (one per lab)
│   ├── lab0_test_connection.py   # Verify credentials and basic model call
│   ├── lab1_hello_agent.py       # First agent, single + multi-turn
│   ├── lab3_file_search.py       # RAG with vector store + policy doc
│   ├── lab4_code_interpreter.py  # Sandboxed Python analytics on claims CSV
│   ├── lab5_function_tools.py    # Custom claim lookup + fraud scoring
│   ├── lab6_multi_tool.py        # All tools combined in one agent
│   ├── lab7_tavily_search.py     # Web search for regulatory intelligence
│   ├── lab8_observability.py     # OTel tracing, metrics, KQL
│   ├── lab9_streaming.py         # Token-by-token streaming output
│   ├── lab10_azure_ai_search.py  # Enterprise RAG with Azure AI Search
│   └── lab11_fastapi_webapp.py   # FastAPI integration + deployment
│
├── labs-notebooks/               # Jupyter notebook versions of each lab
│
├── lab-explanation/              # Visual guides and detailed explanations
│   ├── markdown/                 # Per-lab markdown documentation
│   └── visuals/                  # SVG architecture diagrams per lab
│
├── data/
│   ├── contoso_claims_data.csv   # 500-record insurance claims dataset
│   └── contoso_insurance_policy.md  # Contoso policy document (RAG source)
│
├── utils/
│   ├── config.py                 # Centralized config, client factory, function call loop
│   └── business_functions.py     # Claim lookup + fraud scoring implementations
│
├── outputs/                      # Generated charts and dashboards
├── architecture.svg              # System architecture diagram
├── Dockerfile                    # Production container image
├── requirements.txt              # Python dependencies
├── startup.sh                    # Azure Web App startup script
└── README.md
```

---

## Lab Progression

Each lab builds on the previous one. You can run them independently as Python scripts or Jupyter notebooks.

| Lab | Title | What You Learn |
|-----|-------|----------------|
| **0** | Test Connection | Verify `.env`, credentials, basic model call via Foundry SDK |
| **1** | Hello Agent | Create an agent with instructions, single-turn + multi-turn conversations |
| **3** | File Search (RAG) | Vector store creation, document upload, policy Q&A with citations |
| **4** | Code Interpreter | Sandboxed Python execution, pandas analytics, chart generation |
| **5** | Function Tools | Custom business logic as tools, client-side execution loop |
| **6** | Multi-Tool Agent | Combine all tools — agent picks the right one automatically |
| **7** | Tavily Web Search | Live web search as a function tool for regulatory intelligence |
| **8** | Observability | OpenTelemetry tracing, custom metrics, Azure Monitor, KQL queries |
| **9** | Streaming | Token-by-token output, streaming with function calls |
| **10** | Azure AI Search | Enterprise RAG with hybrid search, security trimming, index management |
| **11** | FastAPI Web App | Full web application + Azure Container App deployment |

---

## How the Agent Tools Work

**File Search (RAG)** — Labs 3, 6. The platform uploads, chunks, embeds, and searches documents automatically. The agent queries the vector store without you writing any search code.

**Code Interpreter** — Labs 4, 6. The platform runs Python in a sandboxed container. The agent writes pandas/matplotlib code internally, executes it, and returns results and charts.

**Custom Functions** — Labs 5, 6, 7. You define a JSON schema and implement the function. The agent calls it when needed, your code executes locally, and you send results back. This is how claim lookup, fraud scoring, and web search work.

**Azure AI Search** — Lab 10. Connects the agent to your existing enterprise search index with hybrid search (vector + keyword), semantic ranking, and per-document access control.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Azure CLI (`az login`)
- An Azure AI Foundry project with GPT-4o-mini deployed
- A `.env` file with:

```
PROJECT_ENDPOINT=https://your-ai-services.services.ai.azure.com/api/projects/your-project
MODEL_DEPLOYMENT_NAME=gpt-4o-mini
TAVILY_API_KEY=tvly-xxxxx          # Optional, for Lab 7
AI_SEARCH_CONNECTION_NAME=...       # Optional, for Lab 10
AI_SEARCH_INDEX_NAME=...            # Optional, for Lab 10
```

### Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run any lab
python labs/lab0_test_connection.py
python labs/lab1_hello_agent.py
python labs/lab3_file_search.py
# ... and so on

# Run the web app locally
uvicorn app.main:app --reload --port 8000
```

### Deploy to Azure Container Apps

```bash
# Build in cloud (no local Docker needed)
az acr build --registry yourACR --image smartclaims-webapp:v1 --file Dockerfile .

# Deploy
az containerapp create \
    --name smartclaims-app \
    --resource-group rg-smartclaims \
    --environment smartclaims-env \
    --image yourACR.azurecr.io/smartclaims-webapp:v1 \
    --target-port 8000 --ingress external \
    --min-replicas 0 --max-replicas 1
```

---

## Technologies

| Layer | Technology |
|-------|-----------|
| AI Platform | Microsoft Foundry Agent Service, Azure OpenAI (GPT-4o-mini) |
| Search | Azure AI Search (hybrid + semantic), Foundry File Search (vector store) |
| Compute | Azure Container Apps, Azure Container Registry |
| Observability | OpenTelemetry, Azure Monitor, Application Insights |
| Web Framework | FastAPI, Gunicorn + Uvicorn |
| Frontend | HTML/CSS/JS, Chart.js |
| Language | Python 3.11 |
| Auth | DefaultAzureCredential, Managed Identity |

---

## SDK Patterns (Foundry v2.x)

**Create and use an agent:**
```python
agent = project_client.agents.create_version(agent_name, definition)
response = openai_client.responses.create(
    extra_body={"agent_reference": {"name": ..., "version": ..., "type": "agent_reference"}},
    input="user message"
)
```

**Function call loop:**
```python
response = openai_client.responses.create(...)
for fc in response.output:          # check for function_call items
    result = my_function(fc.args)   # execute locally
    # send result back via previous_response_id
```

**Streaming:**
```python
stream = openai_client.responses.create(..., stream=True)
for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
```

---

## Data

The project includes two pre-built data files in `data/`:

- **contoso_claims_data.csv** — 500 insurance claim records with fields like claim_id, policy_number, incident_type, claim_amount, status, fraud_flag, fraud_score, region, policy_type, processing_days, and adjuster_name. Used by Code Interpreter (Lab 4) and Function Tools (Lab 5).

- **contoso_insurance_policy.md** — A detailed Contoso insurance policy document covering auto, property, health, life, and liability policies. Used by File Search / RAG (Lab 3).

---

## Credits

Built by **[GENNOOR](https://gennoor.com)** — Enterprise AI Training & Solutions.

GENNOOR partners with organizations to build Copilot fluency, deliver agentic proof-of-concepts, and accelerate AI adoption across Microsoft, AWS, and Google Cloud ecosystems.

---

## License

This project is for educational and demonstration purposes.
#   m i c r o s o f t - f o u n d r y - a g e n t - a z u r e  
 