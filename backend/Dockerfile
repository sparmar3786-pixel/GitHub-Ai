FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir "git+https://github.com/TauricResearch/TradingAgents.git"
COPY app.py advanced.py ollama_status.py .
ENV TRADINGAGENTS_COMMAND=tradingagents
ENV TRADINGAGENTS_ANALYZE_TEMPLATE="tradingagents --ticker {ticker} --date {date} --analysts market,social,news,fundamentals --save --no-show"
ENV TRADINGAGENTS_OUTPUT_LANGUAGE=English
ENV TRADINGAGENTS_MAX_DEBATE_ROUNDS=1
ENV TRADINGAGENTS_MAX_RISK_ROUNDS=1
ENV TRADINGAGENTS_RESULTS_DIR=/data/logs
ENV TRADINGAGENTS_MEMORY_LOG_PATH=/data/memory/trading_memory.md
ENV TRADINGAGENTS_CACHE_DIR=/data/cache
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
