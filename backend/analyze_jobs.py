"""Background execution for long-running TradingAgents research requests.

Render's request proxy may close a long-running HTTP connection. These endpoints
return a job ID quickly and let clients poll for completion instead.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from app import (
    AnalyzeRequest,
    cli_available,
    command_parts,
    configuration_gaps,
    now,
    sanitize_diagnostic,
)

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=max(1, int(os.getenv("TRADINGAGENTS_ANALYZE_WORKERS", "2"))))
_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()
_MAX_JOBS = 100


def _run_job(job_id: str, req: AnalyzeRequest) -> None:
    try:
        if not cli_available():
            raise RuntimeError("TradingAgents CLI is missing on this backend image.")
        gaps = configuration_gaps()
        if gaps:
            raise RuntimeError("Backend setup incomplete (" + ", ".join(gaps) + ").")
        template = os.environ["TRADINGAGENTS_ANALYZE_TEMPLATE"]
        analysis_date = req.date or datetime.now().strftime("%Y-%m-%d")
        analysts = ",".join(req.analysts)
        command = template.format(ticker=req.ticker.upper(), date=analysis_date, analysts=analysts)
        cmd = shlex.split(command)
        if "{analysts}" not in template and "--analysts" not in cmd:
            cmd.extend(["--analysts", analysts])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=int(os.getenv("TRADINGAGENTS_TIMEOUT_SECONDS", "240")),
            check=False,
            env=os.environ.copy(),
        )
        if result.returncode != 0:
            diagnostic = sanitize_diagnostic(result.stderr or result.stdout)
            raise RuntimeError(
                "Upstream analysis failed (exit code "
                + str(result.returncode)
                + "). "
                + (diagnostic or "Check provider/model settings and market-data access.")
            )
        output = (result.stdout or "").strip()
        if not output:
            raise RuntimeError("Upstream returned empty output; no result returned.")
        completed = {
            "status": "READY",
            "ticker": req.ticker.upper(),
            "generated_at": now(),
            "summary": "Research completed by the configured TradingAgents CLI. This is not a guaranteed trade signal or financial advice.",
            "report": output[-20000:],
        }
        with _jobs_lock:
            _jobs[job_id].update(completed)
    except subprocess.TimeoutExpired:
        with _jobs_lock:
            _jobs[job_id].update(status="ERROR", error="Analysis timed out; no result returned.")
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        with _jobs_lock:
            _jobs[job_id].update(status="ERROR", error=str(exc)[:3000])
    except Exception:
        with _jobs_lock:
            _jobs[job_id].update(status="ERROR", error="Unexpected backend error while running analysis.")


@router.post("/v1/analyze/jobs", status_code=202)
def submit_analyze_job(req: AnalyzeRequest):
    """Queue research and return immediately, avoiding long-lived HTTP requests."""
    if not cli_available():
        raise HTTPException(status_code=503, detail="TradingAgents CLI is missing on this backend image.")
    gaps = configuration_gaps()
    if gaps:
        raise HTTPException(status_code=503, detail="Backend setup incomplete (" + ", ".join(gaps) + ").")
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        # Bound memory use; discard oldest completed jobs only.
        if len(_jobs) >= _MAX_JOBS:
            for old_id in list(_jobs):
                if _jobs[old_id].get("status") in {"READY", "ERROR"}:
                    del _jobs[old_id]
                    if len(_jobs) < _MAX_JOBS:
                        break
        if len(_jobs) >= _MAX_JOBS:
            raise HTTPException(status_code=429, detail="Research queue is full. Wait for a running job to finish.")
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "RUNNING",
            "ticker": req.ticker.upper(),
            "created_at": now(),
        }
    _executor.submit(_run_job, job_id, req)
    return {"job_id": job_id, "status": "RUNNING", "ticker": req.ticker.upper()}


@router.get("/v1/analyze/jobs/{job_id}")
def get_analyze_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Research job not found. It may have expired or the backend restarted.")
        return dict(job)
