FROM python:3.11-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /home/smartservice/.local
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/

ENV PATH=/home/smartservice/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/data/chromadb /tmp/smartservice && \
    addgroup --system smartservice && \
    adduser --system --ingroup smartservice smartservice && \
    chown -R smartservice:smartservice /app /tmp/smartservice

USER smartservice

ENV OTEL_METRICS_EXPORTER=none
ENV OTEL_LOGS_EXPORTER=none

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

EXPOSE 8000 9090

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
