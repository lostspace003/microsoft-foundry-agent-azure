"""
SmartClaims — FastAPI Web Application
======================================
Run locally:  uvicorn app.main:app --reload --port 8000
"""

import os
import time
import tempfile
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.agent_service import AgentService
from app.observability import tracer
from opentelemetry.trace import StatusCode

# ─── App Setup ────────────────────────────────────────
app = FastAPI(title="SmartClaims AI Agent", version="1.0")
templates = Jinja2Templates(
    directory=str(Path(__file__).parent / "templates")
)

agent_svc = AgentService()


# ─── Observability Middleware ─────────────────────────

@app.middleware("http")
async def trace_requests(request: Request, call_next):
    """Create a span for every HTTP request."""
    with tracer.start_as_current_span(
        f"{request.method} {request.url.path}",
        attributes={
            "http.method": request.method,
            "http.url": str(request.url),
            "http.route": request.url.path,
        },
    ) as span:
        start = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("duration_seconds", round(duration, 3))
            if response.status_code >= 400:
                span.set_status(StatusCode.ERROR, f"HTTP {response.status_code}")
            else:
                span.set_status(StatusCode.OK)
            return response
        except Exception as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            raise


# ─── Health Check ─────────────────────────────────────

@app.get("/health")
async def health():
    """Health check for monitoring and load balancers."""
    return {"status": "healthy", "version": "1.0.0"}


# ─── Models ───────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

class FraudRequest(BaseModel):
    incident_type: str
    claim_amount: float
    region: str
    days_since_policy_start: int

class ClaimLookup(BaseModel):
    claim_id: str


# ─── Routes ───────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the frontend."""
    # Starlette 0.36+ signature: request is first positional arg
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    tmp_dir = tempfile.mkdtemp()
    file_items = []
    try:
        for f in files:
            ext = Path(f.filename).suffix.lower()
            tmp_path = os.path.join(tmp_dir, f.filename)
            with open(tmp_path, "wb") as out:
                out.write(await f.read())
            if ext == ".csv":
                file_items.append({"path": tmp_path, "filename": f.filename, "type": "csv"})
            elif ext in (".md", ".txt"):
                file_items.append({"path": tmp_path, "filename": f.filename, "type": "doc"})
            else:
                return JSONResponse(status_code=400,
                    content={"error": f"Unsupported format: {ext}. Use .csv, .md, or .txt"})
        if not file_items:
            return JSONResponse(status_code=400, content={"error": "No valid files uploaded."})
        return agent_svc.upload_files(file_items)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    return {"response": agent_svc.chat(req.message)}


@app.post("/api/policy-qa")
async def policy_qa(req: ChatRequest):
    prompt = f"Using the uploaded policy documents, answer: {req.message}. Cite specific sections."
    return {"response": agent_svc.chat(prompt)}


@app.post("/api/analytics")
async def analytics(req: ChatRequest):
    return agent_svc.analytics_chat(req.message)


@app.post("/api/claim-lookup")
async def claim_lookup(req: ClaimLookup):
    return {"response": agent_svc.chat(f"Look up claim {req.claim_id}. Show all details.")}


@app.post("/api/fraud-risk")
async def fraud_risk(req: FraudRequest):
    return {"response": agent_svc.chat(
        f"Calculate fraud risk: {req.incident_type} claim for "
        f"${req.claim_amount:,.2f} in {req.region} region, "
        f"policy started {req.days_since_policy_start} days ago."
    )}


@app.on_event("shutdown")
def shutdown():
    agent_svc.cleanup()