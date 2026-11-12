# DocuMind developer shortcuts. Run `make help` to list targets.
PYTHON ?= python3.12
VENV   := backend/.venv
BIN    := $(VENV)/bin
PY     := $(BIN)/python

.PHONY: help venv install sample-docs qdrant qdrant-down up down test lint format \
        check-embeddings ingest ask api web evals clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

venv: ## Create the backend virtualenv
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip

install: venv ## Install backend with dev dependencies and frontend packages
	$(PY) -m pip install -e "backend[dev]"
	cd frontend && npm install

sample-docs: ## Generate the 8 fictional sample documents into data/sample_docs
	$(PY) scripts/make_sample_docs.py

qdrant: ## Start only Qdrant in Docker
	docker compose up -d qdrant

qdrant-down: ## Stop all compose services
	docker compose down

up: ## Build and start the full stack (qdrant, api, web)
	docker compose up --build -d

down: ## Stop the full stack
	docker compose down

ingest: ## Ingest data/sample_docs into Qdrant + BM25
	cd backend && .venv/bin/python -m app.ingest.pipeline ../data/sample_docs

ask: ## Ask a question from the terminal: make ask Q="Wie lange ist die Gewährleistung?"
	cd backend && .venv/bin/python -m app.rag.answer "$(Q)" --debug

api: ## Run the FastAPI backend with auto-reload on :8000
	cd backend && .venv/bin/uvicorn app.api:app --reload --port 8000

web: ## Run the Next.js dev server on :3000
	cd frontend && npm run dev

test: ## Run backend tests (no API keys needed)
	cd backend && .venv/bin/pytest -q

lint: ## Lint backend and scripts with ruff, typecheck the frontend
	cd backend && .venv/bin/ruff check . ../scripts && .venv/bin/ruff format --check . ../scripts
	cd frontend && npm run typecheck

format: ## Auto-format with ruff
	cd backend && .venv/bin/ruff format . ../scripts && .venv/bin/ruff check --fix . ../scripts

check-embeddings: ## Embed one sentence with the configured EMBEDDING_PROVIDER
	cd backend && .venv/bin/python -c "from app.llm import get_embeddings; e = get_embeddings(); v = e.embed_query('Hydraulikpumpe Wartung'); print(type(e).__name__, 'dim =', len(v))"

evals: ## Run the evaluation suite and write backend/evals/results.md
	cd backend && .venv/bin/python -m evals.run_evals

clean: ## Remove caches and generated indexes
	rm -rf backend/.pytest_cache backend/.ruff_cache data/index frontend/.next
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
