from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1", tags=["TradingAgents advanced"])
DATA_DIR = Path(os.getenv("TRADINGAGENTS_DATA_DIR", "/data"))
RESULTS_DIR = Path(os.getenv("TRADINGAGENTS_RESULTS_DIR", str(DATA_DIR / "results")))
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
PROVIDERS = {
    "openai": ("OPENAI_API_KEY",), "openrouter": ("OPENROUTER_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",), "google": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "nvidia": ("NVIDIA_API_KEY",), "deepseek": ("DEEPSEEK_API_KEY",),
    "groq": ("GROQ_API_KEY",), "xai": ("XAI_API_KEY",), "mistral": ("MISTRAL_API_KEY",),
    "qwen": ("DASHSCOPE_API_KEY", "ALIBABA_API_KEY"), "glm": ("ZHIPUAI_API_KEY",),
    "minimax": ("MINIMAX_API_KEY",), "azure": ("AZURE_OPENAI_API_KEY",),
    "openai_compatible": ("OPENAI_API_KEY",), "ollama": (),
}

def command_parts() -> list[str]:
    return shlex.split(os.getenv("TRADINGAGENTS_COMMAND", "tradingagents"))

def cli_available() -> bool:
    parts = command_parts()
    return bool(parts) and shutil.which(parts[0]) is not None

def configured_providers() -> list[str]:
    result = []
    for provider, keys in PROVIDERS.items():
        if provider == "ollama" and os.getenv("OLLAMA_BASE_URL", "").strip():
            result.append(provider)
        elif any(os.getenv(key, "").strip() for key in keys):
            result.append(provider)
    return result

def gaps() -> list[str]:
    result = []
    provider = os.getenv("TRADINGAGENTS_LLM_PROVIDER", "").strip().lower()
    if provider not in PROVIDERS:
        result.append("TRADINGAGENTS_LLM_PROVIDER")
    elif provider == "ollama":
        if not os.getenv("OLLAMA_BASE_URL", "").strip():
            result.append("OLLAMA_BASE_URL")
    elif not any(os.getenv(k, "").strip() for k in PROVIDERS[provider]):
        result.append("provider API key for " + provider)
    for key in ("TRADINGAGENTS_QUICK_THINK_LLM", "TRADINGAGENTS_DEEP_THINK_LLM",
                "TRADINGAGENTS_OUTPUT_LANGUAGE", "TRADINGAGENTS_MAX_DEBATE_ROUNDS",
                "TRADINGAGENTS_MAX_RISK_ROUNDS", "TRADINGAGENTS_ANALYZE_TEMPLATE"):
        if not os.getenv(key, "").strip():
            result.append(key)
    return result

class Position(BaseModel):
    ticker: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.\-^=]+$")
    quantity: float
    average_price: float | None = Field(default=None, ge=0)

class Portfolio(BaseModel):
    cash: float | None = Field(default=None, ge=0)
    currency: str = Field(default="INR", min_length=1, max_length=8)
    positions: list[Position] = Field(default_factory=list, max_length=100)

class ResearchRun(BaseModel):
    ticker: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.\-^=]+$")
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    analysts: list[Literal["market", "news", "fundamentals", "social"]] = Field(
        default_factory=lambda: ["market", "news", "fundamentals", "social"], min_length=1, max_length=4)
    use_portfolio: bool = True
    checkpoint_enabled: bool = True
    clear_checkpoints: bool = False
    html_report: bool = True
    quick_model: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:/-]+$")
    deep_model: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:/-]+$")
    quick_provider: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    deep_provider: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    output_language: str | None = Field(default=None, min_length=2, max_length=40, pattern=r"^[A-Za-z -]+$")
    debate_rounds: int | None = Field(default=None, ge=1, le=10)
    risk_rounds: int | None = Field(default=None, ge=1, le=10)

class GridRun(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=20)
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    every_n_days: int = Field(default=7, ge=1, le=365)
    analysts: list[Literal["market", "news", "fundamentals", "social"]] = Field(
        default_factory=lambda: ["market", "news", "fundamentals", "social"], min_length=1, max_length=4)
    run_id: str | None = Field(default=None, min_length=1, max_length=80)

@router.get("/portfolio")
def get_portfolio():
    if not PORTFOLIO_FILE.exists():
        return {"configured": False, "cash": None, "currency": "INR", "positions": []}
    try:
        return {"configured": True, **Portfolio.model_validate_json(PORTFOLIO_FILE.read_text(encoding="utf-8")).model_dump()}
    except Exception:
        raise HTTPException(status_code=500, detail="Stored portfolio is invalid; save a valid portfolio again.") from None

@router.put("/portfolio")
def put_portfolio(req: Portfolio):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temp = PORTFOLIO_FILE.with_suffix(".tmp")
        temp.write_text(req.model_dump_json(indent=2), encoding="utf-8")
        temp.replace(PORTFOLIO_FILE)
    except OSError:
        raise HTTPException(status_code=500, detail="Could not save portfolio. Check persistent volume permissions.") from None
    return {"status": "SAVED", "configured": True, **req.model_dump()}

@router.get("/config")
def get_config():
    keys = ("TRADINGAGENTS_LLM_PROVIDER", "TRADINGAGENTS_QUICK_THINK_LLM",
            "TRADINGAGENTS_DEEP_THINK_LLM", "TRADINGAGENTS_QUICK_THINK_PROVIDER",
            "TRADINGAGENTS_DEEP_THINK_PROVIDER", "TRADINGAGENTS_OUTPUT_LANGUAGE",
            "TRADINGAGENTS_MAX_DEBATE_ROUNDS", "TRADINGAGENTS_MAX_RISK_ROUNDS",
            "TRADINGAGENTS_CHECKPOINT_ENABLED")
    return {
        "status": "ok" if cli_available() else "UNAVAILABLE",
        "framework_cli_available": cli_available(),
        "configured_providers": configured_providers(),
        "configuration_gaps": gaps(),
        "settings": {key: os.getenv(key, "") for key in keys},
        "persistent_volume_expected": str(DATA_DIR).startswith("/data"),
        "point_in_time_policy": "Historical correctness depends on the installed framework and timestamped source data; verify reports and provider coverage.",
    }

@router.get("/reports")
def list_reports():
    items = {}
    for root in (RESULTS_DIR, DATA_DIR / "results"):
        try:
            if not root.exists():
                continue
            for item in root.rglob("*"):
                if item.is_symlink() or not item.is_file() or item.suffix.lower() not in {".html", ".md", ".json", ".jsonl", ".txt"}:
                    continue
                try:
                    stat = item.stat()
                    items[str(item.resolve())] = {
                        "name": item.name, "relative_path": str(item.relative_to(root)),
                        "format": item.suffix.lower().lstrip("."), "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    }
                except OSError:
                    pass
        except OSError:
            pass
    return {"reports": sorted(items.values(), key=lambda item: item["modified_at"], reverse=True)[:100],
            "persistent_volume_expected": str(DATA_DIR).startswith("/data")}

@router.get("/reports/open/{filename}")
def open_report(filename: str):
    if filename in {"", ".", ".."} or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid report filename.")
    for root in (RESULTS_DIR, DATA_DIR / "results"):
        candidate = root / filename
        try:
            if candidate.is_symlink() or not candidate.is_file() or candidate.resolve().parent != root.resolve():
                continue
            if candidate.suffix.lower() not in {".html", ".md", ".txt", ".json"}:
                continue
            media_type = "text/html" if candidate.suffix.lower() == ".html" else "text/plain"
            return FileResponse(candidate, media_type=media_type)
        except OSError:
            pass
    raise HTTPException(status_code=404, detail="Report not found in configured results directory.")

@router.post("/checkpoints/clear")
def clear_checkpoints():
    if not cli_available():
        raise HTTPException(status_code=503, detail="TradingAgents CLI is missing; checkpoints were not changed.")
    code = ("from tradingagents.graph.checkpointer import clear_all_checkpoints; "
            "from tradingagents.default_config import DEFAULT_CONFIG; "
            "print(clear_all_checkpoints(DEFAULT_CONFIG['data_cache_dir']))")
    try:
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                                timeout=30, check=False, env=os.environ.copy())
    except (OSError, subprocess.TimeoutExpired):
        raise HTTPException(status_code=500, detail="Could not clear checkpoints; check backend logs.") from None
    if result.returncode:
        raise HTTPException(status_code=502, detail="Checkpoint clear failed; verify the installed framework version.")
    return {"status": "CLEARED", "message": (result.stdout or "").strip() or "Checkpoint clear completed."}

@router.post("/advanced/run")
def advanced_run(req: ResearchRun):
    if not cli_available():
        return {"status": "UNAVAILABLE", "summary": "TradingAgents CLI is missing; no analysis was run.", "report": None}
    try:
        analysis_date = date.fromisoformat(req.date) if req.date else date.today()
    except ValueError:
        raise HTTPException(status_code=422, detail="Analysis date must be a real YYYY-MM-DD date.") from None
    template = os.getenv("TRADINGAGENTS_ANALYZE_TEMPLATE", "").strip()
    if not template:
        raise HTTPException(status_code=503, detail="TRADINGAGENTS_ANALYZE_TEMPLATE is not configured.")
    try:
        command = template.format(ticker=req.ticker.upper(), date=analysis_date.isoformat(), analysts=",".join(req.analysts),
                                  portfolio=str(PORTFOLIO_FILE) if req.use_portfolio and PORTFOLIO_FILE.exists() else "")
        args = shlex.split(command)
    except (KeyError, ValueError):
        raise HTTPException(status_code=500, detail="Invalid TRADINGAGENTS_ANALYZE_TEMPLATE placeholders.") from None
    def has_flag(*flags):
        return any(arg in flags for arg in args)
    # Respect the mobile analyst selection even when the deployment template
    # contains a hard-coded --analysts value.
    if "--analysts" in args:
        analyst_index = args.index("--analysts")
        if analyst_index + 1 >= len(args):
            raise HTTPException(status_code=500, detail="Analyze template has --analysts without a value.")
        args[analyst_index + 1] = ",".join(req.analysts)
    if not has_flag("--ticker"):
        args.extend(["--ticker", req.ticker.upper()])
    if not has_flag("--date"):
        args.extend(["--date", analysis_date.isoformat()])
    if not has_flag("--analysts"):
        args.extend(["--analysts", ",".join(req.analysts)])
    if req.use_portfolio and PORTFOLIO_FILE.exists() and not has_flag("--portfolio"):
        args.extend(["--portfolio", str(PORTFOLIO_FILE)])
    if not has_flag("--checkpoint", "--no-checkpoint"):
        args.append("--checkpoint" if req.checkpoint_enabled else "--no-checkpoint")
    if req.clear_checkpoints and not has_flag("--clear-checkpoints"):
        args.append("--clear-checkpoints")
    if not has_flag("--html", "--no-html"):
        args.append("--html" if req.html_report else "--no-html")
    if not has_flag("--show", "--no-show"):
        args.append("--no-show")
    if not has_flag("--save", "--no-save"):
        args.append("--save")
    run_env = os.environ.copy()
    overrides = {
        "TRADINGAGENTS_QUICK_THINK_LLM": req.quick_model,
        "TRADINGAGENTS_DEEP_THINK_LLM": req.deep_model,
        "TRADINGAGENTS_QUICK_THINK_PROVIDER": req.quick_provider,
        "TRADINGAGENTS_DEEP_THINK_PROVIDER": req.deep_provider,
        "TRADINGAGENTS_OUTPUT_LANGUAGE": req.output_language,
        "TRADINGAGENTS_MAX_DEBATE_ROUNDS": str(req.debate_rounds) if req.debate_rounds is not None else None,
        "TRADINGAGENTS_MAX_RISK_ROUNDS": str(req.risk_rounds) if req.risk_rounds is not None else None,
    }
    allowed_providers = set(PROVIDERS)
    for key, value in overrides.items():
        if value is None:
            continue
        if key.endswith("_PROVIDER") and value.strip().lower() not in allowed_providers:
            raise HTTPException(status_code=422, detail="Unsupported provider value for " + key)
        run_env[key] = value.strip().lower() if key.endswith("_PROVIDER") else value.strip()
    try:
        result = subprocess.run(args, capture_output=True, text=True,
            timeout=int(os.getenv("TRADINGAGENTS_ANALYZE_TIMEOUT_SECONDS", "900")),
            check=False, env=run_env)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Analysis timed out; check backend logs and resume using checkpoints.") from None
    except OSError:
        raise HTTPException(status_code=500, detail="Could not start TradingAgents CLI.") from None
    output = (result.stdout or "").strip()
    if result.returncode:
        detail = (result.stderr or output or "TradingAgents analysis failed.")[-4000:]
        raise HTTPException(status_code=502, detail=detail)
    if not output:
        raise HTTPException(status_code=502, detail="TradingAgents returned no report output.")
    return {"status": "READY", "ticker": req.ticker.upper(), "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": "Analysis completed. Review the saved report and data timestamps before acting.", "report": output[-30000:]}

@router.post("/backtest-grid")
def backtest_grid(req: GridRun):
    if not cli_available():
        return {"status": "UNAVAILABLE", "summary": "TradingAgents CLI is missing; no grid was run.", "report": None}
    try:
        start, end = date.fromisoformat(req.start_date), date.fromisoformat(req.end_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Backtest dates must be real calendar dates.") from None
    if start > end:
        raise HTTPException(status_code=422, detail="Backtest start date must be on or before end date.")
    tickers = []
    for raw in req.tickers:
        ticker = raw.strip().upper()
        if not re.fullmatch(r"[A-Z0-9.\-^=]{1,20}", ticker):
            raise HTTPException(status_code=422, detail="Invalid ticker: " + raw)
        if ticker not in tickers:
            tickers.append(ticker)
    if req.run_id and not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", req.run_id):
        raise HTTPException(status_code=422, detail="run_id may contain letters, digits, underscore and hyphen only.")
    args = [*command_parts(), "backtest", ",".join(tickers), "--start", start.isoformat(),
            "--end", end.isoformat(), "--every", str(req.every_n_days), "--analysts", ",".join(req.analysts)]
    if PORTFOLIO_FILE.exists():
        args.extend(["--portfolio", str(PORTFOLIO_FILE)])
    if req.run_id:
        args.extend(["--run-id", req.run_id])
    try:
        result = subprocess.run(args, capture_output=True, text=True,
            timeout=int(os.getenv("TRADINGAGENTS_BACKTEST_TIMEOUT_SECONDS", "3600")),
            check=False, env=os.environ.copy())
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Backtest grid timed out; use the same run ID to resume if supported.") from None
    except OSError:
        raise HTTPException(status_code=500, detail="Could not start backtest CLI.") from None
    output = (result.stdout or "").strip()
    if result.returncode:
        raise HTTPException(status_code=502, detail=(result.stderr or output or "Backtest grid failed.")[-4000:])
    if not output:
        raise HTTPException(status_code=502, detail="Backtest grid returned empty output.")
    return {"status": "READY", "tickers": tickers, "start_date": start.isoformat(), "end_date": end.isoformat(),
            "run_id": req.run_id, "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": "Framework backtest grid completed; metrics are only those returned by the installed CLI.", "report": output[-30000:]}
