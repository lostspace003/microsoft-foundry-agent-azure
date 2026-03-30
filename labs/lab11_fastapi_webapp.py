"""
Lab 11: FastAPI Web App Deployment
===================================
Run locally:  uvicorn app.main:app --reload --port 8000
Deploy:       python labs/lab11_fastapi_webapp.py
"""

import sys
import os
import subprocess
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.config import print_header, print_step, PROJECT_ROOT


def main():
    print_header(11, "FastAPI Web App Deployment")

    # -- Step 1: Verify Project Structure -------------------
    print_step("Step 1: Verify Project Structure")

    required = {
        "app/main.py":           "FastAPI application entry point",
        "app/agent_service.py":  "Agent orchestration service",
        "app/templates/index.html": "Frontend UI template",
        "requirements.txt":      "Python dependencies",
        "startup.sh":            "Azure App Service startup script",
    }

    all_ok = True
    for path, desc in required.items():
        full = PROJECT_ROOT / path
        exists = full.exists()
        status = "[OK]" if exists else "[MISSING]"
        print(f"   {status} {path:35s} — {desc}")
        if not exists:
            all_ok = False

    if not all_ok:
        print("\n   ERROR: Missing files. Fix before proceeding.")
        return

    # -- Step 2: Verify Dependencies ------------------------
    print_step("Step 2: Verify Key Dependencies")

    deps = ["fastapi", "uvicorn", "jinja2", "python-multipart", "gunicorn", "aiofiles"]
    for pkg in deps:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"   [OK] {pkg}")
        except ImportError:
            print(f"   [MISSING] {pkg} — run: pip install {pkg}")
            all_ok = False

    if not all_ok:
        print("\n   Run: pip install -r requirements.txt")
        return

    # -- Step 3: Explain App Architecture -------------------
    print_step("Step 3: Application Architecture")
    print()
    print("   ┌─────────────────────────────────────────────────┐")
    print("   │              SmartClaims Web App                 │")
    print("   ├─────────────────────────────────────────────────┤")
    print("   │                                                 │")
    print("   │  Browser (index.html + Chart.js)                │")
    print("   │      │                                          │")
    print("   │      ▼                                          │")
    print("   │  FastAPI (app/main.py)                          │")
    print("   │      │  Routes:                                 │")
    print("   │      │  GET  /            → UI                  │")
    print("   │      │  POST /api/upload  → File upload         │")
    print("   │      │  POST /api/chat    → General chat        │")
    print("   │      │  POST /api/policy-qa → Policy Q&A        │")
    print("   │      │  POST /api/analytics → Charts + data     │")
    print("   │      │  POST /api/claim-lookup → Claim status   │")
    print("   │      │  POST /api/fraud-risk  → Fraud scoring   │")
    print("   │      ▼                                          │")
    print("   │  AgentService (app/agent_service.py)            │")
    print("   │      │  • Lazy Azure client init                │")
    print("   │      │  • Vector store for docs (RAG)           │")
    print("   │      │  • Code Interpreter for CSV              │")
    print("   │      │  • Function call loop                    │")
    print("   │      ▼                                          │")
    print("   │  Microsoft Foundry Agent Service                │")
    print("   │      • GPT-4o-mini model                        │")
    print("   │      • File Search + Code Interpreter           │")
    print("   │      • Custom functions (claim/fraud)           │")
    print("   └─────────────────────────────────────────────────┘")

    # -- Step 4: Local Testing Instructions -----------------
    print_step("Step 4: Run Locally")
    print()
    print("   Start the dev server:")
    print("   ┌──────────────────────────────────────────────┐")
    print("   │  uvicorn app.main:app --reload --port 8000   │")
    print("   └──────────────────────────────────────────────┘")
    print()
    print("   Then open: http://localhost:8000")
    print()
    print("   Workflow:")
    print("   1. Upload contoso_claims_data.csv + contoso_insurance_policy.md")
    print("   2. Agent initializes with File Search + Code Interpreter + Functions")
    print("   3. Use tabs: Chat | Policy Q&A | Analytics | Claim Lookup | Fraud Risk")
    print("   4. Analytics tab renders interactive Chart.js charts")

    # -- Step 5: Azure Deployment ---------------------------
    print_step("Step 5: Deploy to Azure Web App")
    print()
    print("   Prerequisites:")
    print("   • Azure CLI installed (az --version)")
    print("   • Logged in (az login)")
    print("   • Resource group created")
    print()

    az_available = shutil.which("az") is not None
    if az_available:
        print("   [OK] Azure CLI detected")
    else:
        print("   [WARN] Azure CLI not found — install from https://aka.ms/installazurecli")

    print()
    print("   Deployment Commands:")
    print("   ┌──────────────────────────────────────────────────────────────────┐")
    print("   │  # 1. Set variables                                             │")
    print("   │  RG=smartclaims-rg                                              │")
    print("   │  APP=smartclaims-webapp                                         │")
    print("   │  PLAN=smartclaims-plan                                          │")
    print("   │  LOCATION=westus3                                               │")
    print("   │                                                                 │")
    print("   │  # 2. Create resource group                                     │")
    print("   │  az group create --name $RG --location $LOCATION                │")
    print("   │                                                                 │")
    print("   │  # 3. Create App Service plan (B1 = Basic tier)                 │")
    print("   │  az appservice plan create \\                                    │")
    print("   │      --name $PLAN --resource-group $RG \\                        │")
    print("   │      --sku B1 --is-linux                                        │")
    print("   │                                                                 │")
    print("   │  # 4. Create web app with Python 3.11                           │")
    print("   │  az webapp create \\                                             │")
    print("   │      --name $APP --resource-group $RG \\                         │")
    print("   │      --plan $PLAN --runtime \"PYTHON:3.11\"                       │")
    print("   │                                                                 │")
    print("   │  # 5. Configure startup and port                                │")
    print("   │  az webapp config set \\                                         │")
    print("   │      --name $APP --resource-group $RG \\                         │")
    print("   │      --startup-file startup.sh                                  │")
    print("   │                                                                 │")
    print("   │  az webapp config appsettings set \\                             │")
    print("   │      --name $APP --resource-group $RG \\                         │")
    print("   │      --settings WEBSITES_PORT=8000                              │")
    print("   │                                                                 │")
    print("   │  # 6. Set environment variables                                 │")
    print("   │  az webapp config appsettings set \\                             │")
    print("   │      --name $APP --resource-group $RG \\                         │")
    print("   │      --settings \\                                               │")
    print("   │        PROJECT_ENDPOINT=\"<your-foundry-endpoint>\" \\             │")
    print("   │        MODEL_DEPLOYMENT_NAME=\"gpt-4o-mini\"                      │")
    print("   │                                                                 │")
    print("   │  # 7. Deploy code (from project root)                           │")
    print("   │  az webapp up \\                                                 │")
    print("   │      --name $APP --resource-group $RG \\                         │")
    print("   │      --runtime \"PYTHON:3.11\"                                    │")
    print("   └──────────────────────────────────────────────────────────────────┘")

    # -- Step 6: Post-Deployment Checklist ------------------
    print_step("Step 6: Post-Deployment Checklist")
    print()
    print("   | Step                     | Command / Action                          |")
    print("   |--------------------------|-------------------------------------------|")
    print("   | Enable Managed Identity  | az webapp identity assign --name $APP     |")
    print("   |                          |     --resource-group $RG                  |")
    print("   | Grant AI User role       | Assign 'Azure AI User' role to the       |")
    print("   |                          | webapp's managed identity in your         |")
    print("   |                          | Foundry project's IAM settings            |")
    print("   | Check logs               | az webapp log tail --name $APP           |")
    print("   |                          |     --resource-group $RG                  |")
    print("   | Test endpoint            | curl https://$APP.azurewebsites.net      |")
    print("   | Enable HTTPS only        | az webapp update --name $APP             |")
    print("   |                          |     --resource-group $RG --https-only     |")

    # -- Step 7: Startup Script Explained -------------------
    print_step("Step 7: Startup Script (startup.sh)")
    print()
    print("   Your startup.sh runs gunicorn with uvicorn workers:")
    print()
    print("   gunicorn app.main:app \\")
    print("       --workers 1 \\")
    print("       --worker-class uvicorn.workers.UvicornWorker \\")
    print("       --bind 0.0.0.0:8000 \\")
    print("       --timeout 120")
    print()
    print("   Key settings:")
    print("   • --workers 1       : Single worker (scale via App Service instances)")
    print("   • --timeout 120     : Allow time for SDK initialization")
    print("   • --bind 0.0.0.0:8000 : Must match WEBSITES_PORT setting")
    print("   • UvicornWorker     : ASGI support for FastAPI async routes")

    # -- Step 8: Security for Production --------------------
    print_step("Step 8: Production Security")
    print()
    print("   | Concern              | Solution                                    |")
    print("   |----------------------|---------------------------------------------|")
    print("   | Authentication       | Use Managed Identity (not .env secrets)     |")
    print("   | CORS                 | Add CORSMiddleware if using separate frontend|")
    print("   | Rate limiting        | Azure API Management or SlowAPI middleware  |")
    print("   | File upload size     | Limit via FastAPI (default 1MB)             |")
    print("   | HTTPS                | Enforce via --https-only                    |")
    print("   | Monitoring           | Enable Application Insights                |")

    # -- Summary -------------------------------------------
    print(f"\n{'='*65}")
    print("  [OK] Lab 11 Complete!")
    print()
    print("  Key files:")
    print("    app/main.py           — FastAPI routes")
    print("    app/agent_service.py  — Agent orchestration")
    print("    app/templates/index.html — Frontend UI")
    print("    startup.sh            — Azure startup script")
    print("    requirements.txt      — All dependencies")
    print()
    print("  Quick start:")
    print("    uvicorn app.main:app --reload --port 8000")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
