# TradingAgents Mobile

Android research client plus FastAPI backend for the open-source [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) framework.

- `android/`: native Android app.
- `backend/`: FastAPI adapter.
- `.github/workflows/android-apk.yml`: builds and uploads a debug APK artifact.

Research only; this app never places orders. Configure provider credentials on the backend only, never in the APK. The backend fails closed when the upstream CLI or its configured command is missing.

## APK
Open GitHub Actions → Android APK → Run workflow. Download `tradingagents-debug-apk` from the completed run's Artifacts section.

## Backend
`cd backend && pip install -r requirements.txt && uvicorn app:app --host 0.0.0.0 --port 8000`

Set `TRADINGAGENTS_COMMAND` and `TRADINGAGENTS_ANALYZE_TEMPLATE` on the server to match the installed upstream TradingAgents CLI. See upstream documentation for provider/data API configuration.

## Attribution
Upstream TradingAgents by Tauric Research: https://github.com/TauricResearch/TradingAgents. Distributed under Apache-2.0; retain upstream copyright, license, and notices with any upstream source copied into this project. This repository adds a separate mobile integration layer.
