FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        chromium-driver \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY api ./api
COPY cs2_analytics ./cs2_analytics
COPY scripts ./scripts

RUN python -m pip install --upgrade pip \
    && python -m pip install .

COPY main.py manage_db.py run_api.py ./

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/logs /app/demos /app/parsed_data \
    && mkdir -p /usr/local/lib/python3.14/site-packages/seleniumbase/drivers \
    && chown -R appuser:appuser \
        /app \
        /usr/local/lib/python3.14/site-packages/seleniumbase/drivers

USER appuser

EXPOSE 8000

CMD ["python", "run_api.py"]
