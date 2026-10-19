# AI-TRADING Mobile UI — GitHub-Ai

The Android APK is built from the Flutter app in `mobile/`, ported from the AI-TRADING repository's `flutter_app/` source. The separate original snapshot remains under `upstream/AI-TRADING/`.

## UI tabs included

The Flutter APK is built from `mobile/`. Its main navigation includes Dashboard, Market, Option Chain, OI Lab, Indicators, Risk, Backtesting, API, Data Health, Broker Home, Signal Calendar, and **AI Research**. The former Signals and Strategies navigation pages are intentionally removed from this APK.

The main navigation has dedicated tabs for AI Research, Analyst Team, Bull/Bear Debate, Trader Decision, Risk & Portfolio, Research Backtest, Reports & Memory, and Provider Status. The pages share the TradingAgents backend connection but open the relevant module by default. Analysis and backtesting require a separately deployed TradingAgents backend. The APK does not run the Python/LangGraph framework locally and does not place broker orders.

## Repository layout

- `mobile/`: Flutter Android app source used to build the APK.
- `android/`: previous native Kotlin prototype; the APK workflow now builds `mobile/`.
- `backend/`: separate FastAPI adapter for the TradingAgents research framework.
- `upstream/AI-TRADING/`: imported AI-TRADING source snapshot.
- `upstream/TradingAgents/`: imported TradingAgents source snapshot and notices.
- `.github/workflows/android-apk.yml`: generates Android platform files, runs Flutter tests, builds a debug APK, and uploads the artifact.

## Build APK

Open [GitHub Actions → Android APK](https://github.com/sparmar3786-pixel/GitHub-Ai/actions/workflows/android-apk.yml). After a successful run, download `ai-trading-ui-debug-apk` from the run's Artifacts section. It is a debug APK, not a Play Store-signed release.

The workflow uses the Flutter source under `mobile/`; changes to the older Kotlin prototype do not automatically change this APK.

## Backend integration status

The Flutter UI is a port of the repository's existing AI-TRADING Flutter app, not a claim that every screen's data path has been newly integrated or verified. The UI uses the backend URLs and endpoints defined in `mobile/lib/config.dart` and `mobile/lib/api.dart`. Verify live Angel One authentication, fresh market data, option-chain completeness, and each screen's endpoint on a deployed backend before relying on any trading display.

The separate `backend/` service wraps the upstream TradingAgents CLI and exposes `/health`, `/v1/analyze`, and `/v1/backtest`. Deploy that service separately, configure its provider/model environment variables, then enter its public HTTPS URL in the AI Research tab. Report persistence is enabled in the backend container CLI template, with results, memory and cache directed under `/data`; mount a persistent Railway volume at `/data` so they survive redeploys. Provider credentials belong on the backend only.

## Safety

- The app is intended for research/signals, not a guarantee of returns.
- A healthy HTTP endpoint does not by itself prove live market ticks or valid signals.
- Do not commit broker credentials, API keys, TOTP seeds, JWTs, refresh tokens, or feed tokens.
- Missing or stale market data must not be treated as an actionable trade.
- Keep upstream licenses and notices with imported source.

## Upstream sources

- AI-TRADING: https://github.com/sparmar3786-pixel/AI-TRADING
- TradingAgents: https://github.com/TauricResearch/TradingAgents
