# Optional Render Ollama service (not provisioned)

This folder documents the planned optional local-model service. It intentionally does **not** add an Ollama service to the root `render.yaml`, change production environment variables, or trigger a deployment. Do not create or upgrade Render resources until the owner explicitly approves the plan and cost.

## Target

- Model: `llama3.2:3b`
- Ollama model directory: `/data/models` on a persistent disk
- Backend provider: `ollama`
- Backend environment: `OLLAMA_BASE_URL` set to the Ollama service's secured base URL, and `OLLAMA_MODEL=llama3.2:3b`
- Quick/deep models: `TRADINGAGENTS_QUICK_THINK_LLM=llama3.2:3b` and `TRADINGAGENTS_DEEP_THINK_LLM=llama3.2:3b`
- Quick/deep providers: `TRADINGAGENTS_QUICK_THINK_PROVIDER=ollama` and `TRADINGAGENTS_DEEP_THINK_PROVIDER=ollama`

The installed TradingAgents version must be checked to confirm the exact Ollama URL/model environment contract before switching production settings. Do not assume that setting the top-level provider alone changes both tier clients.

## Security requirements

Ollama's API is not an authentication boundary. Never expose an unauthenticated Ollama port on a public Render URL. Prefer Render private networking between paid services where supported, or put an authenticated TLS proxy in front of Ollama and allow only the backend to reach it. Do not put access tokens in the URL, source code, or logs. If a secure service-to-service path is unavailable on the selected Render plans, stop and obtain approval for a different hosting design instead of making Ollama public.

## Resource and storage gates

1. Confirm the chosen Render plan's RAM/CPU, disk support, outbound access, private networking and current monthly cost in the dashboard.
2. Use at least 4 GB RAM as an initial sizing target for a 3B quantized model, with 8 GB preferred for operating headroom; validate with actual load tests. Model file size is not total runtime memory.
3. Attach persistent storage at `/data` and configure Ollama to store models under `/data/models`. Ensure free disk is greater than the model download plus update headroom.
4. Download/pull `llama3.2:3b` only after explicit cost approval. Do not download model weights during image build.
5. Run `GET /api/tags` from the backend network and verify `llama3.2:3b` is listed before enabling research.

## Rollout and rollback

1. Merge the code-only PR; no service is provisioned by this PR.
2. Review Render resource costs and service-to-service security; obtain explicit approval.
3. Create the Ollama service and persistent disk manually or through a separately approved infrastructure PR.
4. Set backend variables only after the secured endpoint responds and the model check passes.
5. Verify `/v1/ollama/status`, `/health`, `/v1/config`, then run a small test analysis and inspect logs for model errors.
6. Roll back by restoring the previous provider variables; do not delete persistent model storage until its contents are no longer needed.

The Ollama status endpoint proves only network reachability and model presence. It does not prove that TradingAgents agent runs, market data, or generated trading analysis are correct.
