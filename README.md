# AI Trading Research — Android

A native Android research client with an AI-TRADING-inspired dark navy/teal UI, backed by the open-source [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) multi-agent research framework.

## Components

- `android/`: native Android APK with backend health check, ticker input, research execution and report display.
- `backend/`: FastAPI adapter that invokes the upstream TradingAgents CLI.
- `upstream/TradingAgents/`: imported upstream source snapshot and its license/notices.
- `.github/workflows/android-apk.yml`: builds a debug APK and uploads `tradingagents-debug-apk`.

## Build APK

Open [GitHub Actions → Android APK](https://github.com/sparmar3786-pixel/GitHub-Ai/actions/workflows/android-apk.yml) and choose **Run workflow**. After a successful run, download `tradingagents-debug-apk` from the run's Artifacts section. The APK artifact is a debug build, not a Play Store-signed release.

## Backend setup

The APK does not bundle model credentials and cannot perform AI analysis without a deployed backend.

For a local backend, install the framework and adapter dependencies:

```bash
python -m pip install -r backend/requirements.txt
python -m pip install "git+https://github.com/TauricResearch/TradingAgents.git"
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

For container deployment, build with `backend/Dockerfile` using the repository root as the build context. Set the service's root/build context accordingly.

Configure a supported provider API key on the backend only (for example `OPENROUTER_API_KEY`, `NVIDIA_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GOOGLE_API_KEY`). Set `TRADINGAGENTS_COMMAND` and `TRADINGAGENTS_ANALYZE_TEMPLATE` to match the installed CLI and selected model settings. Configure the market-data providers required by the chosen analysis. The health endpoint detects basic setup only; a successful health response does not prove that provider quota, model access, or market data is working.

After deployment, paste the backend's public HTTPS URL into the APK and tap **CHECK CONNECTION**, then **RUN AI RESEARCH**.

## Safety and limitations

- Research-only app: no broker login, order placement, or automatic execution.
- Provider/API secrets must never be placed in the APK or committed to Git.
- If backend/provider/data access fails, the app reports failure and does not invent a result.
- TradingAgents is a research framework, not a guaranteed strategy or financial advice.
- The starter UI has been adapted to AI-TRADING visual styling; this does not by itself integrate AI-TRADING's Angel One live feed or its options-signal engine.

## Attribution

Upstream TradingAgents by Tauric Research: https://github.com/TauricResearch/TradingAgents. The upstream project is distributed under Apache-2.0; retain upstream copyright, license, and notices with copied upstream source. This repository adds a separate mobile integration layer.
