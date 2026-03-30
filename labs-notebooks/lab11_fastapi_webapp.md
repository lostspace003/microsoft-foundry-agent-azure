# Lab 11: FastAPI Web App — Container App Deployment
---
**SmartClaims AI Agent** | Microsoft Foundry Agent Service (v2.x)

## Objective

Deploy the complete SmartClaims web application using FastAPI and Azure Container Apps. This guide covers:
- Application architecture overview
- Running locally for development and testing
- Deploying to Azure Container Apps (with Dockerfile)
- Managed Identity for passwordless authentication
- Post-deployment security and monitoring

> **Why Container Apps instead of App Service?**
> Azure App Service uses Oryx to detect and install Python dependencies during zip deployment. In practice, Oryx can skip the `pip install` step, causing `ModuleNotFoundError` at startup (e.g., `No module named 'uvicorn'`). A Dockerfile gives you explicit control over dependency installation — `pip install -r requirements.txt` runs as a build step, guaranteeing all packages are present in the image before deployment. Container Apps also offer scale-to-zero cost savings.

---

## Application Architecture

```
+-------------------------------------------------+
|              SmartClaims Web App                 |
+-------------------------------------------------+
|                                                 |
|  Browser (index.html + Chart.js)                |
|      |                                          |
|      v                                          |
|  FastAPI (app/main.py)                          |
|      |  Routes:                                 |
|      |  GET  /            --> UI                |
|      |  POST /api/upload  --> File upload       |
|      |  POST /api/chat    --> General chat      |
|      |  POST /api/policy-qa --> Policy Q&A      |
|      |  POST /api/analytics --> Charts + data   |
|      |  POST /api/claim-lookup --> Claim status |
|      |  POST /api/fraud-risk  --> Fraud scoring |
|      v                                          |
|  AgentService (app/agent_service.py)            |
|      |  - Lazy Azure client init                |
|      |  - Vector store for docs (RAG)           |
|      |  - Code Interpreter for CSV              |
|      |  - Function call loop                    |
|      v                                          |
|  Microsoft Foundry Agent Service                |
|      - GPT-4o-mini model                        |
|      - File Search + Code Interpreter           |
|      - Custom functions (claim/fraud)           |
+-------------------------------------------------+
```

### Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI routes and request handling |
| `app/agent_service.py` | Agent orchestration, resource management, function call loop |
| `app/templates/index.html` | Single-page frontend with tabs (Chat, Policy Q&A, Analytics, etc.) |
| `Dockerfile` | Container image build instructions |
| `.dockerignore` | Excludes venv, .git, .env from container image |
| `startup.sh` | Gunicorn startup script (also used as Dockerfile CMD) |
| `requirements.txt` | All Python dependencies |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve the frontend UI |
| `POST` | `/api/upload` | Upload CSV + policy documents |
| `POST` | `/api/chat` | General conversation with the agent |
| `POST` | `/api/policy-qa` | Policy document Q&A (RAG) |
| `POST` | `/api/analytics` | Data analysis with charts (Chart.js) |
| `POST` | `/api/claim-lookup` | Look up specific claims by ID |
| `POST` | `/api/fraud-risk` | Calculate fraud risk for new claims |

---

## Step 1: Prerequisites

Before deploying, ensure you have:

- [ ] Python 3.10+ with virtual environment activated
- [ ] `.env` file configured (see below)
- [ ] Azure CLI installed (`az --version`)
- [ ] Azure CLI logged in (`az login`)
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `Dockerfile` and `.dockerignore` in project root

> **Note:** You do NOT need Docker installed locally. Azure Container Registry builds the image in the cloud using `az acr build`.

### Required Project Files

```
smart-claims-agent-project/
  app/
    main.py                 -- FastAPI application entry point
    agent_service.py        -- Agent orchestration service
    templates/
      index.html            -- Frontend UI template
  Dockerfile                -- Container image definition
  .dockerignore             -- Files excluded from container
  requirements.txt          -- Python dependencies
  startup.sh                -- Gunicorn startup script
  .env                      -- Environment variables (local dev only)
```

---

## Step 2: Configure Environment Variables

Create or update your `.env` file in the project root (for local development only):

```env
# REQUIRED - Azure AI Foundry
PROJECT_ENDPOINT=<your-foundry-project-endpoint>
MODEL_DEPLOYMENT_NAME=gpt-4o-mini

# OPTIONAL - Azure AI Search (for Lab 10 features)
AI_SEARCH_CONNECTION_NAME=<your-search-connection-name>
AI_SEARCH_INDEX_NAME=<your-search-index-name>

# OPTIONAL - Tavily Web Search (for Lab 7 features)
TAVILY_API_KEY=<your-tavily-api-key>
```

> **Where to find your values:**
> - **PROJECT_ENDPOINT** -- Azure AI Foundry portal > Your Project > Overview > Endpoint
> - **MODEL_DEPLOYMENT_NAME** -- Azure AI Foundry portal > Deployments > Your model name
> - **TAVILY_API_KEY** -- Sign up at [tavily.com](https://tavily.com) (1,000 free searches/month)

---

## Step 3: Run Locally

Start the development server:

```bash
# From the project root directory
uvicorn app.main:app --reload --port 8000
```

Then open: **http://localhost:8000**

### Local Testing Workflow

1. Upload `data/contoso_claims_data.csv` + `data/contoso_insurance_policy.md`
2. Agent initializes with File Search + Code Interpreter + Functions
3. Use tabs: **Chat** | **Policy Q&A** | **Analytics** | **Claim Lookup** | **Fraud Risk**
4. Analytics tab renders interactive Chart.js charts

> **Tip:** The `--reload` flag auto-restarts the server when you modify Python files. Remove it in production.

---

## Step 4: Dockerfile Explained

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

| Design Choice | Why |
|---------------|-----|
| `python:3.11-slim` | Small image, matches project Python version |
| `COPY requirements.txt` first | Layer caching — pip install is cached unless dependencies change |
| `--no-cache-dir` | Reduces image size by not storing pip cache |
| `ENV` in Dockerfile | Ensures tracing env var is present before any Python import |
| `CMD` with gunicorn | Production ASGI server with UvicornWorker for FastAPI async support |

---

## Step 5: Deploy to Azure Container Apps

### 5.1 -- Set Your Variables

Replace the placeholder values below with your own:

```bash
# ---- CHANGE THESE VALUES ----
RG=<your-resource-group>              # e.g., rg-smartclaims
ACR_NAME=<your-acr-name>             # e.g., smartclaimsacr (must be globally unique, alphanumeric only)
ENV_NAME=<your-container-env-name>    # e.g., smartclaims-env
APP_NAME=<your-container-app-name>    # e.g., smartclaims-app
LOCATION=<your-azure-region>          # e.g., westus3, eastus, centralindia
```

### 5.2 -- Create Resource Group

```bash
az group create --name $RG --location $LOCATION
```

### 5.3 -- Create Azure Container Registry

```bash
az acr create \
    --name $ACR_NAME \
    --resource-group $RG \
    --location $LOCATION \
    --sku Basic \
    --admin-enabled true
```

### 5.4 -- Build Image in ACR (Cloud Build)

```bash
# Run from the project root directory (where Dockerfile is)
az acr build \
    --registry $ACR_NAME \
    --image smartclaims-webapp:v1 \
    --file Dockerfile . \
    --no-logs
```

> **Note:** Use `--no-logs` on Windows to avoid Unicode encoding errors in log streaming. No local Docker installation is needed — the build runs entirely in Azure.

### 5.5 -- Create Container Apps Environment

```bash
az containerapp env create \
    --name $ENV_NAME \
    --resource-group $RG \
    --location $LOCATION
```

This auto-creates a Log Analytics workspace for container logs.

### 5.6 -- Get ACR Password

```bash
ACR_PASS=$(az acr credential show \
    --name $ACR_NAME \
    --query "passwords[0].value" -o tsv)
```

### 5.7 -- Deploy Container App

```bash
az containerapp create \
    --name $APP_NAME \
    --resource-group $RG \
    --environment $ENV_NAME \
    --image $ACR_NAME.azurecr.io/smartclaims-webapp:v1 \
    --registry-server $ACR_NAME.azurecr.io \
    --registry-username $ACR_NAME \
    --registry-password "$ACR_PASS" \
    --target-port 8000 \
    --ingress external \
    --min-replicas 0 --max-replicas 1 \
    --cpu 1.0 --memory 2.0Gi \
    --env-vars \
        PROJECT_ENDPOINT="<your-foundry-endpoint>" \
        MODEL_DEPLOYMENT_NAME="gpt-4o-mini" \
        AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING="true"
```

| Setting | Value | Why |
|---------|-------|-----|
| `--target-port 8000` | Match the gunicorn bind port | Container Apps routes external HTTPS to this port |
| `--ingress external` | Public access | Auto-provisions TLS certificate |
| `--min-replicas 0` | Scale to zero | $0 cost when idle |
| `--max-replicas 1` | Single instance | Scale horizontally if needed later |
| `--cpu 1.0 --memory 2.0Gi` | Container resources | Sufficient for SDK init + agent calls |

### 5.8 -- Verify Deployment

```bash
# Get the app URL
APP_FQDN=$(az containerapp show \
    --name $APP_NAME \
    --resource-group $RG \
    --query "properties.configuration.ingress.fqdn" -o tsv)

echo "App URL: https://$APP_FQDN"

# Test health endpoint
curl https://$APP_FQDN/health
# Expected: {"status":"healthy","version":"1.0.0"}
```

Your app will be available at: `https://<app-name>.<env-id>.<region>.azurecontainerapps.io`

---

## Step 6: Enable Managed Identity

### 6.1 -- Assign System Managed Identity

```bash
PRINCIPAL_ID=$(az containerapp identity assign \
    --name $APP_NAME \
    --resource-group $RG \
    --system-assigned \
    --query "principalId" -o tsv)
```

### 6.2 -- Grant Cognitive Services User Role

```bash
SUB_ID=$(az account show --query id -o tsv)

az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Cognitive Services User" \
    --scope /subscriptions/$SUB_ID/resourceGroups/$RG
```

> **Security:** With Managed Identity, `DefaultAzureCredential` in `agent_service.py` automatically detects and uses the identity — no secrets or API keys needed in environment variables.

---

## Step 7: Post-Deployment Checklist

| Step | Command / Action |
|------|-----------------|
| Verify health | `curl https://$APP_FQDN/health` |
| Check logs | `az containerapp logs show --name $APP_NAME --resource-group $RG` |
| Test all tabs | Upload files, try Chat, Policy Q&A, Analytics, Claim Lookup, Fraud Risk |
| Enable monitoring | Set `APPLICATIONINSIGHTS_CONNECTION_STRING` env var for Azure Monitor |
| Review scaling | Set `--min-replicas 1` if cold starts are unacceptable |

---

## Step 8: Updating the Deployment

To redeploy after code changes:

```bash
# 1. Rebuild image with new tag
az acr build \
    --registry $ACR_NAME \
    --image smartclaims-webapp:v2 \
    --file Dockerfile . \
    --no-logs

# 2. Update container app to use new image
az containerapp update \
    --name $APP_NAME \
    --resource-group $RG \
    --image $ACR_NAME.azurecr.io/smartclaims-webapp:v2
```

---

## Step 9: Production Security

| Concern | Solution |
|---------|----------|
| Authentication | Use **Managed Identity** (not `.env` secrets) |
| CORS | Add `CORSMiddleware` if using a separate frontend domain |
| Rate limiting | Azure API Management or `SlowAPI` middleware |
| File upload size | Limit via FastAPI config (default 1MB) |
| HTTPS | Container Apps auto-provisions TLS certificates |
| Monitoring | Enable **Application Insights** for telemetry and alerts |
| Secrets | Use **Azure Key Vault** or Container App secrets for any API keys |
| Scaling | Adjust `--min-replicas` and `--max-replicas` for traffic patterns |

> **Key Rule:** Never store secrets in `.env` files in production. Use Managed Identity for Azure services and Container App secrets for third-party keys.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Check Dockerfile has `RUN pip install -r requirements.txt` |
| Container exits code 1 | Check logs: `az containerapp logs show --name $APP_NAME --resource-group $RG` |
| Container exits code 127 | `startup.sh` has Windows line endings (CRLF). Fix: `sed -i 's/\r$//' startup.sh` |
| 401 Unauthorized from Foundry | Managed Identity not assigned or role not granted. Re-run Step 6 |
| Unicode error during `az acr build` | Use `--no-logs` flag on Windows to skip log streaming |
| Health returns 503 | Container still starting. Wait 30-60s for gunicorn + SDK init |
| Scale-to-zero cold start | First request after idle takes ~30s. Set `--min-replicas 1` to keep warm |

---

## Quick Reference

```bash
# Local development
uvicorn app.main:app --reload --port 8000

# Build and deploy
az acr build --registry $ACR_NAME --image smartclaims-webapp:v1 --file Dockerfile . --no-logs
az containerapp create --name $APP_NAME --resource-group $RG --environment $ENV_NAME ...

# Check logs
az containerapp logs show --name $APP_NAME --resource-group $RG

# Update deployment
az acr build --registry $ACR_NAME --image smartclaims-webapp:v2 --file Dockerfile . --no-logs
az containerapp update --name $APP_NAME --resource-group $RG --image $ACR_NAME.azurecr.io/smartclaims-webapp:v2
```

---

## Lab 11 Complete -- Course Complete!

### Full Learning Journey

| Lab | Topic | Key Capability |
|-----|-------|---------------|
| 0 | Test Connection | SDK setup and authentication |
| 1 | Hello Agent | Agent creation and conversations |
| 2 | Generate Data | Synthetic dataset for testing |
| 3 | File Search | RAG with Vector Stores |
| 4 | Code Interpreter | Sandboxed Python analytics |
| 5 | Function Tools | Custom business logic |
| 6 | Multi-Tool | Unified agent with all tools |
| 7 | Web Search | Real-time regulatory intelligence |
| 8 | Production | Tracing, versioning, security |
| 8 | Deep Observability | Tracing, metrics, monitoring |
| 9 | Streaming | Real-time token-by-token UX |
| 10 | Azure AI Search | Enterprise-grade RAG |
| **11** | **Container App Deployment** | **Production web application** |
