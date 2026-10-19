from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="TradingAgents Mobile API", version="0.3.0")

PROVIDER_KEY_GROUPS = {
    "openai": ("OPENAI_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "google": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "nvidia": ("NVIDIA_API_KEY",),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "xai": ("XAI_API_KEY",),
    "mistral": ("MISTRAL_API_KEY",),
    "qwen": ("DASHSCOPE_API_KEY", "ALIBABA_API_KEY"),
    "glm": ("ZHIPUAI_API_KEY",),
    "minimax": ("MINIMAX_API_KEY",),
    "azure": ("AZURE_OPENAI_API_KEY",),
    "openai_compatible": ("OPENAI_API_KEY",),
    "ollama": (),
}
ALL_PROVIDER_KEYS = tuple(dict.fromkeys(name for names in PROVIDER_KEY_GROUPS.values() for name in names))


class AnalyzeRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.\-^=]+$")
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    analysts: list[Literal["market", "news", "fundamentals", "social"]] = Field(
        default_factory=lambda: ["market", "news", "fundamentals", "social"],
        min_length=1,
        max_length=4,
    )


class AnalyzeResponse(BaseModel):
    status: Literal["READY", "UNAVAILABLE", "ERROR"]
    ticker: str
    generated_at: str
    summary: str
    report: str | None = None

class BacktestRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.\-^=]+$")
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    every_n_days: int = Field(default=7, ge=1, le=365)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_parts() -> list[str]:
    return shlex.split(os.getenv("TRADINGAGENTS_COMMAND", "tradingagents"))


def cli_available() -> bool:
    parts = command_parts()
    return bool(parts) and shutil.which(parts[0]) is not None


def configured_providers() -> list[str]:
    configured = []
    for provider, env_names in PROVIDER_KEY_GROUPS.items():
        if provider == "ollama" and os.getenv("OLLAMA_BASE_URL", "").strip():
            configured.append(provider)
        elif any(os.getenv(name, "").strip() for name in env_names):
            configured.append(provider)
    return configured


def configuration_gaps() -> list[str]:
    gaps = []
    provider = os.getenv("TRADINGAGENTS_LLM_PROVIDER", "").strip().lower()
    if not provider:
        gaps.append("TRADINGAGENTS_LLM_PROVIDER")
    elif provider not in PROVIDER_KEY_GROUPS:
        gaps.append("supported TRADINGAGENTS_LLM_PROVIDER value")
    else:
        env_names = PROVIDER_KEY_GROUPS[provider]
        if provider == "ollama":
            if not os.getenv("OLLAMA_BASE_URL", "").strip():
                gaps.append("OLLAMA_BASE_URL")
        elif not any(os.getenv(name, "").strip() for name in env_names):
            gaps.append("provider API key for " + provider)
    for name in (
        "TRADINGAGENTS_QUICK_THINK_LLM",
        "TRADINGAGENTS_DEEP_THINK_LLM",
        "TRADINGAGENTS_OUTPUT_LANGUAGE",
        "TRADINGAGENTS_MAX_DEBATE_ROUNDS",
        "TRADINGAGENTS_MAX_RISK_ROUNDS",
    ):
        if not os.getenv(name, "").strip():
            gaps.append(name)
    if not os.getenv("TRADINGAGENTS_ANALYZE_TEMPLATE", "").strip():
        gaps.append("TRADINGAGENTS_ANALYZE_TEMPLATE")
    return gaps


@app.post("/v1/backtest")
def backtest(req: BacktestRequest):
    if not cli_available():
        return {
            "status": "UNAVAILABLE",
            "ticker": req.ticker.upper(),
            "summary": "TradingAgents CLI is missing on the backend. No backtest was run.",
            "report": None,
            "generated_at": now(),
        }
    try:
        start = datetime.strptime(req.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(req.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Backtest dates must be real calendar dates in YYYY-MM-DD format.") from None
    if start > end:
        raise HTTPException(status_code=422, detail="Backtest start date must be on or before end date.")
    gaps = configuration_gaps()
    if gaps:
        return {
            "status": "UNAVAILABLE",
            "ticker": req.ticker.upper(),
            "summary": "Backend setup incomplete (" + ", ".join(gaps) + "). No backtest was run.",
            "report": None,
            "generated_at": now(),
        }

    cmd = [
        *command_parts(),
        "backtest",
        req.ticker.upper(),
        "--start", req.start_date,
        "--end", req.end_date,
        "--every", str(req.every_n_days),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=int(os.getenv("TRADINGAGENTS_BACKTEST_TIMEOUT_SECONDS", "360")),
            check=False,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Backtest timed out; no result returned.") from None
    except OSError:
        raise HTTPException(status_code=500, detail="Could not start the configured TradingAgents CLI.") from None

    if result.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail="Upstream backtest failed. Check backend logs, provider credentials, historical data access and model settings.",
        )
    output = (result.stdout or "").strip()
    if not output:
        raise HTTPException(status_code=502, detail="Upstream backtest returned empty output; no result returned.")
    return {
        "status": "READY",
        "ticker": req.ticker.upper(),
        "generated_at": now(),
        "summary": "Historical backtest completed by TradingAgents CLI. Results depend on the configured model and data.",
        "report": output[-20000:],
    }


@app.get("/health")
def health():
    available = cli_available()
    providers = configured_providers()
    gaps = configuration_gaps()
    ready = available and not gaps
    if not available:
        message = "TradingAgents CLI is missing from this backend image."
    elif gaps:
        message = "API reachable, but non-interactive research setup is incomplete: " + ", ".join(gaps)
    else:
        message = (
            "Required CLI settings and provider credentials were detected. "
            "A live run is still needed to verify model access, quota and market-data sources."
        )
    return {
        "status": "ok",
        "service": "tradingagents-mobile-api",
        "framework_cli_available": available,
        "provider_configured": bool(providers),
        "configured_providers": providers,
        "analysis_ready": ready,
        "configuration_gaps": gaps,
        "message": message,
        "timestamp": now(),
    }


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    if not cli_available():
        return AnalyzeResponse(
            status="UNAVAILABLE",
            ticker=req.ticker.upper(),
            generated_at=now(),
            summary="TradingAgents CLI is missing on the backend. No research result generated.",
        )
    gaps = configuration_gaps()
    if gaps:
        return AnalyzeResponse(
            status="UNAVAILABLE",
            ticker=req.ticker.upper(),
            generated_at=now(),
            summary="Backend setup incomplete (" + ", ".join(gaps) + "). No research result generated.",
        )

    template = os.environ["TRADINGAGENTS_ANALYZE_TEMPLATE"]
    analysis_date = req.date or datetime.now().strftime("%Y-%m-%d")
    analysts = ",".join(req.analysts)
    try:
        command = template.format(
            ticker=req.ticker.upper(),
            date=analysis_date,
            analysts=analysts,
        )
        cmd = shlex.split(command)
        # Existing deployments may already pin analysts in the template.
        # Otherwise honor the selection sent by the app.
        if "{analysts}" not in template and "--analysts" not in cmd:
            cmd.extend(["--analysts", analysts])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=500,
            detail="Invalid TRADINGAGENTS_ANALYZE_TEMPLATE placeholders.",
        ) from None
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=int(os.getenv("TRADINGAGENTS_TIMEOUT_SECONDS", "240")),
            check=False,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Analysis timed out; no result returned.") from None
    except (OSError, ValueError):
        raise HTTPException(status_code=500, detail="Could not start the configured analysis command.") from None

    if result.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail="Upstream analysis failed. Check backend logs, provider credentials, model selection, and data-source access.",
        )
    output = (result.stdout or "").strip()
    if not output:
        raise HTTPException(status_code=502, detail="Upstream returned empty output; no result returned.")

    return AnalyzeResponse(
        status="READY",
        ticker=req.ticker.upper(),
        generated_at=now(),
        summary=(
            "Research completed by the configured TradingAgents CLI. "
            "This is not a guaranteed trade signal or financial advice."
        ),
        report=output[-20000:],
    )


# Additional research workflows are isolated in a router so the original API remains compatible.
from advanced import router as advanced_router
app.include_router(advanced_router)
