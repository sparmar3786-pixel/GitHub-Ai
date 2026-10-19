# AI-TRADING Mobile UI — GitHub-Ai

The Android APK is built from the Flutter app in `mobile/`, ported from the AI-TRADING repository's `flutter_app/` source. The separate original snapshot remains under `upstream/AI-TRADING/`.

## UI tabs included

The Flutter app's tab navigation includes Dashboard, Market, Option Chain, OI Lab, Indicators, Signals, Risk, Backtesting, API, Data Health, Broker Home, Strategies, Quant Engine, Quant Signal, Strategy Signal, and Signal Calendar. The imported source files are kept as the starting point rather than recreating those screens in the former one-screen Kotlin prototype.

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

The separate `backend/` service wraps the upstream TradingAgents CLI. It is not automatically connected to the mobile app just because both sources are in this repository. Provider credentials belong on the backend only.

## Safety

- The app is intended for research/signals, not a guarantee of returns.
- A healthy HTTP endpoint does not by itself prove live market ticks or valid signals.
- Do not commit broker credentials, API keys, TOTP seeds, JWTs, refresh tokens, or feed tokens.
- Missing or stale market data must not be treated as an actionable trade.
- Keep upstream licenses and notices with imported source.

## Upstream sources

- AI-TRADING: https://github.com/sparmar3786-pixel/AI-TRADING
- TradingAgents: https://github.com/TauricResearch/TradingAgents
