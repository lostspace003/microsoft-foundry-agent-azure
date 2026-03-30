# Lab 11: FastAPI Web App — Container App Deployment

## What It Does
Wraps everything from Labs 1-10 into a web application using FastAPI and deploys it to Azure Container Apps with a Dockerfile for reliable production builds. Uses Managed Identity for passwordless authentication and supports scale-to-zero for cost savings.

## Why Container Apps Instead of App Service
Azure App Service uses Oryx to detect and install Python dependencies during zip deployment. In practice, Oryx can skip the `pip install` step, causing `ModuleNotFoundError` at startup (e.g., `No module named 'uvicorn'`). A Dockerfile gives you explicit control over dependency installation -- `pip install -r requirements.txt` runs as a build step, guaranteeing all packages are present in the image before deployment.

## Flow

```
  Developer machine
    |
    |  az acr build (cloud build, no local Docker needed)
    |
    v
  Azure Container Registry (ACR)
    |   Image: smartclaims-webapp:v1
    |   Base: python:3.11-slim
    |   Includes: pip install + app code + gunicorn/uvicorn
    |
    v
  Azure Container App
    |   Ingress: external HTTPS (auto TLS)
    |   Scale: 0-1 replicas (scale to zero when idle)
    |   CPU: 1.0 / Memory: 2.0 GiB
    |   System Managed Identity enabled
    |
    |   Environment Variables:
    |     PROJECT_ENDPOINT       = Foundry project URL
    |     MODEL_DEPLOYMENT_NAME  = gpt-4o-mini
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
  FastAPI (app/main.py)
    |   Routes: /, /api/upload, /api/chat, /api/policy-qa,
    |           /api/analytics, /api/claim-lookup, /api/fraud-risk
    |
    v
  AgentService (app/agent_service.py)
    |   Lazy client initialization
    |   Vector store for docs
    |   Code Interpreter for CSV
    |   Function call loop for custom tools
    |
    v
  Microsoft Foundry Agent Service (cloud)
    |   Authenticated via DefaultAzureCredential
    |   (picks up Managed Identity automatically in Container App)

  Local:  uvicorn app.main:app --reload --port 8000
  Azure:  Dockerfile → ACR → Container App (gunicorn + UvicornWorker)
```

## Key Concepts

- **Azure Container App** -- serverless container hosting with auto-scaling and built-in HTTPS
- **Azure Container Registry (ACR)** -- private Docker registry; `az acr build` builds in the cloud (no local Docker needed)
- **Dockerfile** -- explicit build instructions, eliminates Oryx dependency issues
- **Scale to zero** -- `--min-replicas 0` means the app stops when idle, saving costs
- **FastAPI** -- modern Python web framework with async support
- **AgentService** -- singleton that manages agent lifecycle
- **Lazy initialization** -- Azure clients created on first request, not at startup
- **gunicorn + uvicorn** -- production ASGI server (defined in Dockerfile CMD)
- **Managed Identity** -- use in production instead of .env secrets
- **DefaultAzureCredential** -- Azure SDK credential chain that auto-detects the best auth method

## Deployment Steps (Container Apps)
1. Create resource group + Azure Container Registry (ACR)
2. Build image in ACR with `az acr build` (cloud build, no local Docker needed)
3. Create Container Apps environment
4. Deploy Container App with ACR image, target port 8000, external ingress
5. Set environment variables: PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME
6. Enable system Managed Identity + assign Cognitive Services User role
7. Verify via `/health` endpoint and browser test
