# Multi-stage production Dockerfile for ArcPay Bot
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir --no-warn-script-location -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN useradd -m -u 1000 botuser

COPY --from=builder /root/.local /home/botuser/.local
COPY --chown=botuser:botuser bot/ ./bot/
COPY --chown=botuser:botuser requirements.txt .

RUN mkdir -p /app/data && chown -R botuser:botuser /app

USER botuser

ENV PATH=/home/botuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=10000

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:10000/').read()" || exit 1

CMD ["python", "-m", "bot.main"]
