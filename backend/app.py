from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="TradingAgents Mobile API", version="0.2.0")

# Keep provider secrets on the backend. This is a readiness hint, not proof that
# the provider account, quota, model name, or market-data sources are healthy.
PROVIDER_KEY_GROUPS = {
    "OpenAI": ("OPENAI_API_KEY",),
    "OpenRouter": ("OPENROUTER_API_KEY",),
    "Anthropic": ("ANTHROPIC_API_KEY",),
    "Google": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "NVIDIA": ("NVIDIA_API_KEY",),
    "DeepSeek": ("DEEPSEEK_API_KEY",),
    "Groq": ("GROQ_API_KEY",),
    "xAI": ("XAI_API_KEY",),
    "Mistral": ("MISTRAL_API_KEY",),
    "DashScope / Qwen": ("DASHSCOPE_API_KEY", "ALIBABA_API_KEY"),
    "Zhipu / GLM": ("ZHIPUAI_API_KEY",),
    "MiniMax": ("MINIMAX_API_KEY",),
    "Azure OpenAI": ("AZURE_OPENAI_API_KEY",),
}


class AnalyzeRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.\-^=]+$")
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class AnalyzeResponse(BaseModel):
    status: Literal["READY", "UNAVAILABLE", "ERROR"]
    ticker: str
    generated_at: str
    summary: str
    report: str | None = None


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_parts() -> list[str]:
    return shlex.split(os.getenv("TRADINGAGENTS_COMMAND", "tradingagents"))


def configured_providers() -> list[str]:
    return [
        provider
        for provider, env_names in PROVIDER_KEY_GROUPS.items()
        if any(os.getenv(name, "").strip() for name in env_names)
    ]


def cli_available() -> bool:
    parts = command_parts()
    return bool(parts) and shutil.which(parts[0]) is not None


@app.get("/health")
def health():
    available = cli_available()
    providers = configured_providers()
    template = os.getenv("TRADINGAGENTS_ANALYZE_TEMPLATE", "").strip()
    ready = available and bool(providers) and bool(template)
    if not available:
        message = "TradingAgents CLI is missing from this backend image."
    elif not providers:
        message = "API reachable; configure at least one supported model-provider key on the backend."
    elif not template:
        message = "API reachable; TRADINGAGENTS_ANALYZE_TEMPLATE is not configured."
    else:
        message = "Framework CLI and at least one provider key detected. A live analysis is still required to verify provider and data-source access."
    return {
        "status": "ok",
        "service": "tradingagents-mobile-api",
        "framework_cli_available": available,
        "provider_configured": bool(providers),
        "configured_providers": providers,
        "analysis_ready": ready,
        "message": message,
        "timestamp": now(),
    }


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    parts = command_parts()
    if not parts or shutil.which(parts[0]) is None:
        return AnalyzeResponse(
            status="UNAVAILABLE",
            ticker=req.ticker.upper(),
            generated_at=now(),
            summary="TradingAgents CLI is not installed on this backend. No research result generated.",
        )

    providers = configured_providers()
    if not providers:
        return AnalyzeResponse(
            status="UNAVAILABLE",
            ticker=req.ticker.upper(),
            generated_at=now(),
            summary="No supported model-provider key was detected on the backend. Configure a provider key; no recommendation generated.",
        )

    template = os.getenv(
        "TRADINGAGENTS_ANALYZE_TEMPLATE",
        "tradingagents --ticker {ticker} --date {date}",
    ).strip()
    if not template:
        return AnalyzeResponse(
            status="UNAVAILABLE",
            ticker=req.ticker.upper(),
            generated_at=now(),
            summary="TRADINGAGENTS_ANALYZE_TEMPLATE is not configured. No research result generated.",
        )

    cmd = template.format(ticker=req.ticker.upper(), date=req.date or "")
    try:
        result = subprocess.run(
            shlex.split(cmd),
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
        # Keep provider credentials and raw subprocess logs out of the public API.
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
            "This output is not a guaranteed trade signal or financial advice."
        ),
        report=output[-20000:],
    )
