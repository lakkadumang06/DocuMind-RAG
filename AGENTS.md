# AGENTS.md

Guidance for Codex (and other coding agents) working in this repository.

## What this project is

DocuMind is a RAG knowledge assistant for industrial company documents (PDF, DOCX, TXT in
English and German). It answers only from the indexed documents, cites the exact source
chunk for every claim, and refuses with "I don't know" when retrieval finds nothing
relevant or the model replies `NO_ANSWER`.

- Backend: Python 3.12, FastAPI, LangChain core interfaces, Qdrant, rank-bm25, Pydantic v2
- Frontend: Next.js 16 (App Router), TypeScript, Tailwind CSS 4
- Default models: Gemini (`gemini-3.5-flash` for answers, `gemini-embedding-001` for vectors)

## Commands

Run from the repo root unless a `cd` is shown. The backend venv lives in `backend/.venv`.

```bash
# services
docker compose up -d qdrant                       # vector DB on :6333 (dashboard /dashboard)

# backend
make install                                      # venv + pip install -e "backend[dev]"
make test                                         # pytest, no API keys or Docker needed
make lint                                         # ruff check
make format                                       # ruff format + fix
make sample-docs                                  # regenerate data/sample_docs
cd backend && .venv/bin/python -m app.ingest.pipeline ../data/sample_docs [--force]
cd backend && .venv/bin/python -m app.rag.answer "question" [--mode dense|bm25|hybrid] [--debug]
cd backend && .venv/bin/uvicorn app.api:app --reload --port 8000   # API, docs at /docs

# frontend
cd frontend && npm install
cd frontend && npm run dev                        # http://localhost:3000
cd frontend && npm run typecheck && npm run build

# everything in containers
docker compose up --build                         # qdrant :6333, api :8000, web :3000
```

Before calling a change done, run `make test`, `make lint` and, for frontend changes,
`npm run typecheck && npm run build` in `frontend/`.

## Layout

```
backend/app/
  config.py        Settings via pydantic-settings; the ONLY place that reads env vars (.env at repo root)
  llm.py           get_llm() / get_embeddings() for openai|anthropic|gemini|groq|ollama, PRICES table
  schemas.py       Pydantic models shared by every layer and the API (Chunk, Citation, ChatAnswer, ...)
  ingest/          parsers.py -> chunking.py -> store.py (Qdrant) + bm25_index.py, orchestrated by pipeline.py
  retrieval/       vector.py (dense), bm25.py, hybrid.py (Reciprocal Rank Fusion), rerank.py (LLM, off by default)
  rag/             prompts.py, memory.py (session history + query rewrite), answer.py (RagAnswerer + CLI)
  api.py           FastAPI routes; AppState wires everything; /chat streams Server-Sent Events
backend/tests/     pytest suite using in-memory Qdrant, DeterministicFakeEmbedding and fake chat models
frontend/          app/page.tsx, components/ (Sidebar, Chat, AnswerText, CitationPanel, DebugPanel), lib/api.ts
scripts/           make_sample_docs.py (fictional "Rheintal Antriebstechnik GmbH" documents)
data/              sample_docs/ (committed), index/ and uploads/ (generated, gitignored)
docs/              architecture.md, screenshots
```

## How a question is answered

1. `rewrite_query` turns a follow-up into a standalone question (only if the session has history).
2. `HybridRetriever` runs dense (Qdrant cosine) and BM25, fuses with RRF (k=60), normalises to [0, 1].
3. If the top score is below `MIN_RELEVANCE_SCORE`, refuse without calling the LLM.
4. The model gets numbered passages, must cite as `[n]`, answer in the question's language,
   or reply `NO_ANSWER`, and end with `CONFIDENCE: x`.
5. `RagAnswerer.stream()` yields `token` events, then one `final` event with a `ChatAnswer`.
   Markers are mapped back to retrieved chunks to build `Citation` objects.

`answer()` drains `stream()`; keep a single code path for streaming and non-streaming.

## Conventions

- Only `app/llm.py` imports provider SDKs (`langchain_openai`, `langchain_google_genai`, ...).
  Everything else uses `BaseChatModel` / `Embeddings`.
- Only `app/config.py` reads the environment. Pass `Settings` objects around; tests build
  them with `Settings(_env_file=None, ...)` or `model_copy(update=...)`.
- Tests must run without network, API keys or Docker. Use the fixtures in
  `backend/tests/conftest.py` (`memory_store`, `fake_embeddings`, `test_settings`) and
  `FakeListChatModel`. Never call a real provider in tests.
- Read model output with `message.text`, never `str(message.content)`. Gemini 3 and other
  newer models stream a list of content blocks plus thought signatures.
- Every new default model in `DEFAULT_CHAT_MODELS` / `DEFAULT_EMBEDDING_MODELS` needs a
  `PRICES` entry; a test enforces this.
- Type hints and docstrings on public functions, `logging` instead of `print` (CLIs may print
  their final output). Ruff, line length 100.
- No placeholders or TODOs. Keep code simple enough to explain in an interview.
- Frontend types in `frontend/lib/types.ts` mirror `backend/app/schemas.py` by hand. Change
  both together.
- Commit messages use gitmoji and a plain, human summary of what changed and why, e.g.
  `🐛 Strip inline confidence markers from answers`.

## Gotchas

- **Changing the embedding model changes the vector size** (nomic-embed-text 768,
  gemini-embedding-001 3072). The existing Qdrant collection then rejects upserts. Use a new
  `QDRANT_COLLECTION` name or delete the collection, then re-ingest with `--force`.
- **Re-ingesting skips unchanged files** because the document id is the SHA-256 of the file.
  `data/index/manifest.json` is the source of truth for `GET /documents`; `--force` rebuilds.
- **Hosted model names expire.** `gemini-2.5-flash` is closed to new keys and the preview
  models disappear. Check available models before changing `LLM_MODEL`.
- BM25 uses `BM25Plus` and a small EN/DE stopword list. Plain Okapi gives IDF 0 on tiny
  corpora, which caused false refusals.
- The SSE stream may use `\r\n` line endings; parsers in tests and `frontend/lib/api.ts`
  normalise them.
- The API creates the LLM lazily, so it boots without a key; the first `/chat` then reports
  the missing key as an `error` event.
- Conversation memory is in-process. It is lost on restart and not shared between workers.
- **Ephemeral disks lose `data/index`** (Render free plan, on every restart). `AppState.from_settings`
  calls `pipeline.restore_from_vector_store()`, which rebuilds the manifest and BM25 from the Chunk
  payloads in Qdrant. It mutates the existing `BM25Index`, because the retriever shares that object.
- `.env` is gitignored and holds real keys. Never print, log or commit its values.
