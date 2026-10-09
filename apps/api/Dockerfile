FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install .

COPY providers.toml ./
RUN useradd --create-home --uid 10001 app && mkdir -p /data && chown app /data
USER app

ENV PROVIDERS_FILE=/app/providers.toml \
    DATABASE_URL=sqlite:////data/scribe.db \
    STORAGE_DIR=/data/audio
VOLUME ["/data"]
EXPOSE 8000
CMD ["uvicorn", "--factory", "scribe.main:app_factory", "--host", "0.0.0.0", "--port", "8000"]
