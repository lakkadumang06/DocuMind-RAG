# Build from the repository root so the sample documents can be copied in:
#   docker build -f backend/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --upgrade pip && pip install .

# Sample documents ship with the image; uploads and the BM25 index are written next to them.
COPY data/sample_docs ./data/sample_docs
ENV DATA_DIR=/app/data SAMPLE_DOCS_DIR=/app/data/sample_docs INDEX_DIR=/app/data/index

# Render and most PaaS hosts inject PORT; fall back to 8000 for local Docker.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.api:app --host 0.0.0.0 --port ${PORT}"]
