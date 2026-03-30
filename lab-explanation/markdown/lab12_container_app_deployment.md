# Lab 12: Azure Container App Deployment with Observability & Managed Identity

## What It Does
Deploys the SmartClaims web application (Labs 1-11) as an Azure Container App with integrated OpenTelemetry observability from Lab 8, system-assigned Managed Identity for passwordless authentication, and a custom Dockerfile for reliable production builds. Replaces the App Service approach (Lab 11) with a container-based deployment that eliminates Oryx build issues and provides scale-to-zero cost savings.

## Why Container App Instead of App Service
Azure App Service uses Oryx to detect and install Python dependencies during zip deployment. In practice, Oryx can skip the `pip install` step, causing `ModuleNotFoundError` at startup (e.g., `No module named 'uvicorn'`). A Dockerfile gives you explicit control over dependency installation -- `pip install -r requirements.txt` runs as a build step, guaranteeing all packages are present in the image before deployment.

## Flow

```
  Developer machine
    |
    |  az acr build (cloud build, no local Docker needed)
    |
    v
  Azure Container Registry (smartclaimsacr)
    |   Image: smartclaims-webapp:v1
    |   Base: python:3.11-slim
    |   Includes: pip install + app code + gunicorn/uvicorn
    |
    v
  Azure Container App (smartclaims-app)
    |   Environment: smartclaims-env (West US 3)
    |   Ingress: external HTTPS (auto TLS)
    |   Scale: 0-1 replicas (scale to zero when idle)
    |   CPU: 1.0 / Memory: 2.0 GiB
    |   System Managed Identity enabled
    |
    |   Environment Variables:
    |     PROJECT_ENDPOINT     = Foundry project URL
    |     MODEL_DEPLOYMENT_NAME = gpt-4o-mini
    |     AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING = true
    |
    v
  Application Startup (inside container)
    |
    |  gunicorn app.main:app
    |    --workers 1
    |    --worker-class uvicorn.workers.UvicornWorker
    |    --bind 0.0.0.0:8000
    |    --timeout 120
    |
    v
  app/observability.py (initialized at import time)
    |   Detects APPLICATIONINSIGHTS_CONNECTION_STRING:
    |     Set     --> Azure Monitor (configure_azure_monitor)
    |     Not set --> Console exporters (dev mode)
    |   Exports: tracer, meter, 4 custom metrics
    |
    v
  app/main.py (FastAPI)
    |   Middleware: trace_requests() -- span per HTTP request
    |   Health: GET /health --> {"status":"healthy","version":"1.0.0"}
    |   Routes: /, /api/upload, /api/chat, /api/policy-qa,
    |           /api/analytics, /api/claim-lookup, /api/fraud-risk
    |
    v
  app/agent_service.py (instrumented)
    |   chat() -- wrapped in "agent.chat" span
    |     Tracks: active sessions, duration, token usage
    |     Catches: ClientAuthenticationError, HttpResponseError
    |     Records: request_counter, latency_histogram, token_counter
    |   analytics_chat() -- wrapped in "agent.analytics_chat" span
    |
    v
  Microsoft Foundry Agent Service (cloud)
    |   Authenticated via DefaultAzureCredential
    |   (picks up Managed Identity automatically in Container App)
    |
    v
  User accesses: https://smartclaims-app.<env-id>.westus3.azurecontainerapps.io/
```

## Architecture Diagram

```
  +-------------------+      +------------------------+      +---------------------+
  |   Azure Container |      |  Azure Container App   |      |  Microsoft Foundry  |
  |   Registry (ACR)  |----->|  smartclaims-app        |----->|  Agent Service      |
  |   smartclaimsacr  |      |                        |      |  (gpt-4o-mini)      |
  +-------------------+      |  Managed Identity ------+----->|                     |
                              |  (passwordless auth)   |      +---------------------+
                              |                        |
                              |  OpenTelemetry  -------+----->  Azure Monitor /
                              |  (traces + metrics)    |        Application Insights
                              |                        |
                              |  FastAPI + Gunicorn    |      +---------------------+
                              |  Port 8000             |      |  Azure AI Search    |
                              |  HTTPS (auto TLS)      |      |  smartclaims-search |
                              +------------------------+      +---------------------+
                                        ^
                                        |
                              +-------------------+
                              |  Browser (User)   |
                              |  index.html +     |
                              |  Chart.js         |
                              +-------------------+
```

## Files Created / Modified

| File | Action | Purpose |
|------|--------|---------|
| `Dockerfile` | **Created** | Python 3.11-slim, pip install, gunicorn CMD |
| `.dockerignore` | **Created** | Excludes venv, .git, .env, __pycache__, notebooks |
| `app/observability.py` | **Created** | OpenTelemetry init (Azure Monitor or console) |
| `app/main.py` | **Modified** | Added tracing middleware + /health endpoint |
| `app/agent_service.py` | **Modified** | Instrumented chat() and analytics_chat() with spans/metrics |
| `startup.sh` | **Modified** | Added AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true |
| `.env.example` | **Modified** | Added APPLICATIONINSIGHTS_CONNECTION_STRING |

## Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "app.main:app", "--workers", "1",
     "--worker-class", "uvicorn.workers.UvicornWorker",
     "--bind", "0.0.0.0:8000", "--timeout", "120"]
```

Key design choices:
- **python:3.11-slim** -- small image, matches project Python version
- **Layer caching** -- `COPY requirements.txt` before `COPY .` so pip install is cached unless dependencies change
- **--no-cache-dir** -- reduces image size by not storing pip cache
- **ENV set in Dockerfile** -- ensures tracing env var is present before any Python import

## Observability Integration (from Lab 8)

The `app/observability.py` module initializes OpenTelemetry once at import time:

```
  Import observability.py
    |
    |  load_dotenv() (safe to double-call)
    |
    +---> APPLICATIONINSIGHTS_CONNECTION_STRING set?
    |       YES --> configure_azure_monitor() (production)
    |       NO  --> ConsoleSpanExporter + ConsoleMetricExporter (dev)
    |
    v
  Exports available to app/main.py and app/agent_service.py:
    tracer          -- creates spans for request tracing
    meter           -- creates metrics instruments
    request_counter -- agent.request.count (Counter)
    latency_histogram -- agent.request.duration (Histogram)
    token_counter   -- agent.tokens.used (Counter)
    active_sessions -- agent.active_sessions (UpDownCounter)
```

**HTTP Middleware** (app/main.py):
- Every request gets a span with: method, URL, route, status code, duration
- Errors (4xx/5xx) set span status to ERROR with exception recording

**Agent Instrumentation** (app/agent_service.py):
- `chat()` wrapped in `agent.chat` span with token tracking and error classification
- `analytics_chat()` wrapped in `agent.analytics_chat` span
- Catches: `ClientAuthenticationError`, `HttpResponseError` (including 429 rate limiting)

## Managed Identity

```
  Container App (smartclaims-app)
    |
    |  System-assigned Managed Identity
    |  Principal ID: auto-generated
    |
    +---> Role: "Cognitive Services User"
    |     Scope: rg-smartclaims resource group
    |
    v
  DefaultAzureCredential (in agent_service.py)
    |
    |  Automatically detects Managed Identity in Azure
    |  (falls back to az login locally)
    |
    v
  Authenticates to:
    - Microsoft Foundry (smartclaims-aiservices)
    - Azure AI Search (smartclaims-search)
    - OpenAI API (via Foundry project)
```

No secrets or API keys needed in environment variables. `DefaultAzureCredential` picks up the Managed Identity automatically when running in Azure Container Apps.

## Key Concepts

- **Azure Container App** -- serverless container hosting with auto-scaling, built-in HTTPS, and managed identity support
- **Azure Container Registry (ACR)** -- private Docker registry for storing container images
- **az acr build** -- cloud-based Docker build (no local Docker installation needed)
- **Scale to zero** -- `--min-replicas 0` means the app stops when idle, saving costs
- **System Managed Identity** -- Azure-managed service principal, no credentials to rotate
- **DefaultAzureCredential** -- Azure SDK credential chain that auto-detects the best auth method
- **Dockerfile** -- explicit build instructions, eliminates Oryx dependency issues
- **.dockerignore** -- prevents venv, .git, .env from being included in the container image
- **OpenTelemetry middleware** -- automatic span creation for every HTTP request
- **Health endpoint** -- `/health` for container orchestrator probes and monitoring

## Deployment Steps

### Prerequisites
- Azure CLI installed (`az --version`)
- Logged in (`az login`)
- Resource group `rg-smartclaims` exists in West US 3
- AI Services (`smartclaims-aiservices`) and Foundry project (`smartclaims-project`) already deployed

### Step 1: Create Container Registry
```bash
az acr create --name smartclaimsacr \
    --resource-group rg-smartclaims \
    --location westus3 \
    --sku Basic --admin-enabled true
```

### Step 2: Build Image in ACR (cloud build)
```bash
cd smart-claims-agent-project

az acr build --registry smartclaimsacr \
    --image smartclaims-webapp:v1 \
    --file Dockerfile . --no-logs
```
Note: Use `--no-logs` on Windows to avoid Unicode encoding errors in log streaming.

### Step 3: Create Container Apps Environment
```bash
az containerapp env create \
    --name smartclaims-env \
    --resource-group rg-smartclaims \
    --location westus3
```
This auto-creates a Log Analytics workspace for container logs.

### Step 4: Get ACR Password
```bash
ACR_PASS=$(az acr credential show --name smartclaimsacr \
    --query "passwords[0].value" -o tsv)
```

### Step 5: Deploy Container App
```bash
az containerapp create \
    --name smartclaims-app \
    --resource-group rg-smartclaims \
    --environment smartclaims-env \
    --image smartclaimsacr.azurecr.io/smartclaims-webapp:v1 \
    --registry-server smartclaimsacr.azurecr.io \
    --registry-username smartclaimsacr \
    --registry-password "$ACR_PASS" \
    --target-port 8000 \
    --ingress external \
    --min-replicas 0 --max-replicas 1 \
    --cpu 1.0 --memory 2.0Gi \
    --env-vars \
        PROJECT_ENDPOINT="https://smartclaims-aiservices.services.ai.azure.com/api/projects/smartclaims-project" \
        MODEL_DEPLOYMENT_NAME="gpt-4o-mini" \
        AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING="true"
```

### Step 6: Verify Health
```bash
APP_FQDN=$(az containerapp show --name smartclaims-app \
    --resource-group rg-smartclaims --query "properties.configuration.ingress.fqdn" -o tsv)

curl https://$APP_FQDN/health
# Expected: {"status":"healthy","version":"1.0.0"}
```

### Step 7: Enable Managed Identity
```bash
PRINCIPAL_ID=$(az containerapp identity assign \
    --name smartclaims-app \
    --resource-group rg-smartclaims \
    --system-assigned --query "principalId" -o tsv)
```

### Step 8: Assign Cognitive Services User Role
```bash
SUB_ID=$(az account show --query id -o tsv)

az rest --method put \
    --url "https://management.azure.com/subscriptions/$SUB_ID/resourceGroups/rg-smartclaims/providers/Microsoft.Authorization/roleAssignments/$(python -c 'import uuid;print(uuid.uuid4())')?api-version=2022-04-01" \
    --body "{
        \"properties\": {
            \"roleDefinitionId\": \"/subscriptions/$SUB_ID/providers/Microsoft.Authorization/roleDefinitions/a97b65f3-24c7-4388-baec-2e87135dc908\",
            \"principalId\": \"$PRINCIPAL_ID\",
            \"principalType\": \"ServicePrincipal\"
        }
    }"
```
Note: Role definition `a97b65f3-24c7-4388-baec-2e87135dc908` is "Cognitive Services User".

### Step 9: Open in Browser
```
https://<app-name>.<env-id>.westus3.azurecontainerapps.io/
```

## Azure Resources (rg-smartclaims, West US 3)

| Resource | Type | Purpose |
|----------|------|---------|
| `smartclaims-aiservices` | Cognitive Services | AI Services (GPT-4o-mini) |
| `smartclaims-project` | AI Foundry Project | Agent management |
| `smartclaims-search` | AI Search | Enterprise knowledge base (Lab 10) |
| `smartclaimsacr` | Container Registry | Docker image storage |
| `smartclaims-env` | Container Apps Environment | Hosting environment + Log Analytics |
| `smartclaims-app` | Container App | The deployed web application |

## Updating the Deployment

To redeploy after code changes:

```bash
# 1. Rebuild image with new tag
az acr build --registry smartclaimsacr \
    --image smartclaims-webapp:v2 \
    --file Dockerfile . --no-logs

# 2. Update container app to use new image
az containerapp update \
    --name smartclaims-app \
    --resource-group rg-smartclaims \
    --image smartclaimsacr.azurecr.io/smartclaims-webapp:v2
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Check Dockerfile has `RUN pip install -r requirements.txt` |
| Container exits code 1 | Check logs: `az containerapp logs show --name smartclaims-app --resource-group rg-smartclaims` |
| Container exits code 127 | startup.sh has Windows line endings (CRLF). Fix: `sed -i 's/\r$//' startup.sh` |
| 401 Unauthorized from Foundry | Managed Identity not assigned or role not granted. Re-run Steps 7-8 |
| Unicode error during `az acr build` | Use `--no-logs` flag on Windows to skip log streaming |
| Health returns 503 | Container still starting. Wait 30-60s for gunicorn + SDK init |
| Scale-to-zero cold start | First request after idle takes ~30s. Set `--min-replicas 1` to keep warm |

## App Service vs Container App Comparison

```
  App Service (Lab 11)              Container App (Lab 12)
  -------------------------         -------------------------
  Oryx builds (may skip pip)        Dockerfile (explicit pip install)
  startup.sh required               CMD in Dockerfile
  B1 Basic tier ($13/mo)            Scale to zero ($0 when idle)
  Always running                    0-N replicas auto-scale
  WEBSITES_PORT config              --target-port flag
  az webapp up                      az acr build + az containerapp create
  Managed Identity via webapp       Managed Identity via containerapp
  App Service Logs                  Log Analytics + az containerapp logs
```

## Production Checklist

- [ ] Set `APPLICATIONINSIGHTS_CONNECTION_STRING` env var for Azure Monitor telemetry
- [ ] Verify Managed Identity has Cognitive Services User role
- [ ] Test all tabs: Chat, Policy Q&A, Analytics, Claim Lookup, Fraud Risk
- [ ] Check `/health` endpoint returns 200
- [ ] Review container logs for OTel trace output
- [ ] Consider `--min-replicas 1` if cold starts are unacceptable
- [ ] Enable HTTPS-only (Container Apps does this by default)
- [ ] Set up Azure Monitor alerts (from Lab 8 KQL queries)
