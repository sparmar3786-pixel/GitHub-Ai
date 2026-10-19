from __future__ import annotations
import os, shlex, shutil, subprocess
from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="TradingAgents Mobile API", version="0.1.0")
class AnalyzeRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.\-^=]+$")
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
class AnalyzeResponse(BaseModel):
    status: Literal["READY", "UNAVAILABLE", "ERROR"]
    ticker: str
    generated_at: str
    summary: str
    report: str | None = None

def now(): return datetime.now(timezone.utc).isoformat()
def command_parts(): return shlex.split(os.getenv("TRADINGAGENTS_COMMAND", "tradingagents"))

@app.get("/health")
def health():
    parts = command_parts()
    available = bool(parts) and shutil.which(parts[0]) is not None
    return {"status":"ok","service":"tradingagents-mobile-api","framework_cli_available":available,"analysis_ready":available and bool(os.getenv("TRADINGAGENTS_ANALYZE_TEMPLATE")),"timestamp":now()}

@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    parts = command_parts()
    if not parts or shutil.which(parts[0]) is None:
        return AnalyzeResponse(status="UNAVAILABLE", ticker=req.ticker.upper(), generated_at=now(), summary="TradingAgents CLI is not installed on this backend. No signal generated.")
    template = os.getenv("TRADINGAGENTS_ANALYZE_TEMPLATE")
    if not template:
        return AnalyzeResponse(status="UNAVAILABLE", ticker=req.ticker.upper(), generated_at=now(), summary="TRADINGAGENTS_ANALYZE_TEMPLATE is not configured. No signal generated.")
    cmd = template.format(ticker=req.ticker.upper(), date=req.date or "")
    try:
        result = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=int(os.getenv("TRADINGAGENTS_TIMEOUT_SECONDS","240")), check=False, env=os.environ.copy())
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Analysis timed out; no result returned.")
    if result.returncode != 0: raise HTTPException(status_code=502, detail="Upstream analysis failed; check backend logs.")
    output = (result.stdout or "").strip()
    if not output: raise HTTPException(status_code=502, detail="Upstream returned empty output; no result returned.")
    return AnalyzeResponse(status="READY", ticker=req.ticker.upper(), generated_at=now(), summary="Research completed. This is not a guaranteed trade signal.", report=output[-20000:])
