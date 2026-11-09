# DocuMind developer shortcuts. Run `make help` to list targets.
PYTHON ?= python3.12
VENV   := backend/.venv
BIN    := $(VENV)/bin
PY     := $(BIN)/python

.PHONY: help venv install sample-docs qdrant qdrant-down test lint format check-embeddings clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

venv: ## Create the backend virtualenv
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip

install: venv ## Install backend with dev dependencies
	$(PY) -m pip install -e "backend[dev]"

sample-docs: ## Generate the 8 fictional sample documents into data/sample_docs
	$(PY) scripts/make_sample_docs.py

qdrant: ## Start Qdrant in Docker
	docker compose up -d qdrant

qdrant-down: ## Stop Qdrant
	docker compose down

test: ## Run backend tests (no API keys needed)
	cd backend && .venv/bin/pytest -q

lint: ## Lint backend and scripts with ruff
	cd backend && .venv/bin/ruff check . ../scripts

format: ## Auto-format with ruff
	cd backend && .venv/bin/ruff format . ../scripts && .venv/bin/ruff check --fix . ../scripts

check-embeddings: ## Embed one sentence with the configured EMBEDDING_PROVIDER
	cd backend && .venv/bin/python -c "from app.llm import get_embeddings; e = get_embeddings(); v = e.embed_query('Hydraulikpumpe Wartung'); print(type(e).__name__, 'dim =', len(v))"

clean: ## Remove caches and generated index
	rm -rf backend/.pytest_cache backend/.ruff_cache data/index
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
