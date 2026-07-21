FROM python:3.12-slim-trixie

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

COPY pyproject.toml uv.lock ./

# Install dependencies pinned by uv.lock so image builds are reproducible
# instead of drifting to whatever pip resolves at build time. uv itself is
# pinned so the export step cannot change behavior between builds. Runs
# before the source COPY so this layer stays cached across code changes.
RUN python -m pip install --upgrade pip "uv==0.11.23" \
    && uv export --frozen --no-default-groups --no-emit-project \
        --format requirements-txt -o /tmp/requirements.txt \
    && python -m pip install -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY README.md ./
COPY api ./api
COPY cs2_analytics ./cs2_analytics
COPY scripts ./scripts

RUN python -m pip install --no-deps .

COPY main.py manage_db.py run_api.py ./

RUN site_packages="$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')" \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/logs \
    && mkdir -p "${site_packages}/seleniumbase/drivers" \
    && chown -R appuser:appuser \
        /app \
        "${site_packages}/seleniumbase/drivers"

USER appuser

EXPOSE 8000

CMD ["python", "run_api.py"]
