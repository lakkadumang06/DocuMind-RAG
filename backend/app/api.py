"""FastAPI application: document management and streaming chat.

Run locally:  uvicorn app.api:app --reload --port 8000
Docs:         http://localhost:8000/docs
"""

from __future__ import annotations

import json
import logging
import shutil
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from sse_starlette.sse import EventSourceResponse
from starlette.concurrency import iterate_in_threadpool

from app import __version__
from app.config import Settings, get_settings
from app.ingest.parsers import SUPPORTED_EXTENSIONS
from app.ingest.pipeline import IngestionPipeline
from app.ingest.store import VectorStore
from app.rag.answer import RagAnswerer
from app.rag.memory import ConversationMemory
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.rerank import LLMReranker
from app.retrieval.vector import DenseRetriever
from app.schemas import ChatRequest, DocumentInfo, HealthResponse

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """Everything the endpoints need. Built once at startup, or from fakes in tests."""

    settings: Settings
    embeddings: Embeddings
    store: VectorStore
    pipeline: IngestionPipeline
    retriever: HybridRetriever
    memory: ConversationMemory = field(default_factory=ConversationMemory)
    _llm: BaseChatModel | None = None
    _answerer: RagAnswerer | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> AppState:
        from app.llm import get_embeddings

        embeddings = get_embeddings(settings=settings)
        store = VectorStore(embeddings, settings=settings)
        pipeline = IngestionPipeline(embeddings, store, settings=settings)
        try:  # the local index is lost on hosts with an ephemeral disk; Qdrant still has it
            pipeline.restore_from_vector_store()
        except Exception:  # noqa: BLE001 - never block startup; /health reports Qdrant state
            logger.exception("could not restore the index from Qdrant")
        retriever = HybridRetriever(
            DenseRetriever(store),
            BM25Retriever(index=pipeline.bm25),  # same object: ingestion updates are visible
            default_mode=settings.retrieval_mode,
            top_k=settings.top_k,
            candidate_k=settings.candidate_k,
        )
        return cls(settings, embeddings, store, pipeline, retriever)

    @property
    def answerer(self) -> RagAnswerer:
        """The LLM is created lazily so the API starts even if the key is missing;
        the first chat request then fails with a clear 503 instead of a crash at boot."""
        if self._answerer is None:
            if self._llm is None:
                from app.llm import get_llm

                self._llm = get_llm(settings=self.settings)
            reranker = LLMReranker(self._llm) if self.settings.enable_rerank else None
            self._answerer = RagAnswerer(
                self._llm, self.retriever, self.memory, reranker, self.settings
            )
        return self._answerer


def create_app(state: AppState | None = None) -> FastAPI:
    """Build the FastAPI app. Pass a prepared AppState (with fakes) in tests."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.documind = state or AppState.from_settings(get_settings())
        s = app.state.documind.settings
        logger.info(
            "DocuMind API %s ready (llm=%s, embeddings=%s, qdrant=%s)",
            __version__,
            s.llm_provider,
            s.embedding_provider,
            s.qdrant_url,
        )
        yield

    app = FastAPI(
        title="DocuMind API",
        version=__version__,
        description="RAG knowledge assistant: upload documents, ask questions, get cited answers.",
        lifespan=lifespan,
    )
    settings = state.settings if state else get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


def get_state(request: Request) -> AppState:
    return request.app.state.documind


State = Annotated[AppState, Depends(get_state)]


from fastapi import APIRouter  # noqa: E402  (router defined after helpers for readability)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(state: State) -> HealthResponse:
    reachable = state.store.is_reachable()
    return HealthResponse(
        status="ok" if reachable else "degraded",
        llm_provider=state.settings.llm_provider,
        embedding_provider=state.settings.embedding_provider,
        qdrant_reachable=reachable,
        documents=len(state.pipeline.list_documents()),
    )


@router.get("/documents", response_model=list[DocumentInfo], tags=["documents"])
def list_documents(state: State) -> list[DocumentInfo]:
    return state.pipeline.list_documents()


@router.post(
    "/documents",
    response_model=list[DocumentInfo],
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
async def upload_documents(
    state: State,
    files: Annotated[list[UploadFile], File(description="PDF, DOCX or TXT files")],
) -> list[DocumentInfo]:
    """Upload one or more files and ingest them. A file with the same name as an existing
    document replaces it. Unchanged files are skipped (content hash)."""
    upload_dir = state.settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    results: list[DocumentInfo] = []
    for upload in files:
        name = Path(upload.filename or "upload").name
        if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Unsupported file type for '{name}'. Use pdf, docx or txt.",
            )
        target = upload_dir / name
        with target.open("wb") as fh:
            shutil.copyfileobj(upload.file, fh)
        previous = state.pipeline.manifest.by_filename(name)
        try:
            info = state.pipeline.ingest_file(target)
        except ValueError as exc:
            target.unlink(missing_ok=True)
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        if previous and previous.id != info.id:
            state.pipeline.delete_document(previous.id)
        results.append(info)
    return results


@router.post(
    "/documents/samples",
    response_model=list[DocumentInfo],
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
def load_sample_documents(state: State) -> list[DocumentInfo]:
    """Ingest the bundled sample documents from `data/sample_docs`, so a new user can try
    the assistant without uploading anything. Already indexed files are skipped."""
    directory = state.settings.sample_docs_dir
    if not directory.is_dir():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No sample documents at {directory}. Run `make sample-docs` first.",
        )
    return state.pipeline.ingest_directory(directory)


@router.delete(
    "/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["documents"]
)
def delete_document(document_id: str, state: State) -> None:
    info = state.pipeline.manifest.documents.get(document_id)
    if info is None or not state.pipeline.delete_document(document_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown document id '{document_id}'")
    (state.settings.data_dir / "uploads" / info.filename).unlink(missing_ok=True)


def _sse_events(state: AppState, request: ChatRequest) -> Iterator[dict[str, str]]:
    """Sync generator of SSE events; runs in a worker thread via iterate_in_threadpool."""
    try:
        for event in state.answerer.stream(request):
            if event.type == "token":
                yield {"event": "token", "data": json.dumps({"text": event.token})}
            elif event.answer is not None:
                yield {"event": "final", "data": event.answer.model_dump_json()}
    except Exception as exc:  # noqa: BLE001 - report to the client instead of a dead stream
        logger.exception("chat failed")
        yield {"event": "error", "data": json.dumps({"detail": str(exc)})}


@router.post("/chat", tags=["chat"])
async def chat(request: ChatRequest, state: State) -> EventSourceResponse:
    """Stream the answer as Server-Sent Events.

    Events: `token` {text}, then one `final` with the full ChatAnswer (citations,
    confidence, answer_found, retrieved chunks), or `error` {detail}.
    """
    if not state.pipeline.list_documents():
        raise HTTPException(
            status.HTTP_409_CONFLICT, "No documents ingested yet. Upload one first."
        )
    return EventSourceResponse(iterate_in_threadpool(_sse_events(state, request)))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["chat"])
def clear_session(session_id: str, state: State) -> None:
    """Forget the conversation memory of a session."""
    state.memory.clear(session_id)


app = create_app()
