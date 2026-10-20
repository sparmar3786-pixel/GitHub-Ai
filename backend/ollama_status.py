from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


DEFAULT_MODEL = "llama3.2:3b"


def inspect_ollama(base_url: str | None = None, model: str | None = None, timeout: float = 3.0) -> dict:
    """Check Ollama reachability and model presence without exposing endpoint details."""
    configured_url = (base_url if base_url is not None else os.getenv("OLLAMA_BASE_URL", "")).strip()
    expected_model = (model if model is not None else os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)).strip() or DEFAULT_MODEL
    if not configured_url:
        return {
            "configured": False,
            "reachable": False,
            "model": expected_model,
            "model_available": False,
            "status": "UNCONFIGURED",
            "message": "OLLAMA_BASE_URL is not configured.",
        }

    try:
        parts = urlsplit(configured_url)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("invalid URL")
        if parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("URL must not contain credentials, query or fragment")
        # Keep an optional base path, but never duplicate a trailing slash.
        base_path = parts.path.rstrip("/")
        endpoint = urlunsplit((parts.scheme, parts.netloc, base_path + "/api/tags", "", ""))
        request = Request(endpoint, headers={"Accept": "application/json"}, method="GET")
        with urlopen(request, timeout=max(0.1, min(float(timeout), 10.0))) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = payload.get("models", []) if isinstance(payload, dict) else []
        names = {
            str(item.get("name") or item.get("model") or "")
            for item in models
            if isinstance(item, dict)
        }
        available = expected_model in names
        return {
            "configured": True,
            "reachable": True,
            "model": expected_model,
            "model_available": available,
            "status": "READY" if available else "MODEL_MISSING",
            "message": "Ollama responded and the configured model is available."
            if available
            else "Ollama responded, but the configured model is not installed.",
        }
    except (ValueError, TypeError):
        return {
            "configured": True,
            "reachable": False,
            "model": expected_model,
            "model_available": False,
            "status": "INVALID_CONFIGURATION",
            "message": "OLLAMA_BASE_URL must be an HTTP(S) base URL without credentials, query or fragment.",
        }
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return {
            "configured": True,
            "reachable": False,
            "model": expected_model,
            "model_available": False,
            "status": "UNREACHABLE",
            "message": "Ollama could not be reached. Check service availability, network access and timeout.",
        }
