"""API tests with FastAPI's TestClient, in-memory Qdrant, fake embeddings and a fake LLM."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.api import AppState, create_app
from app.config import Settings
from app.ingest.pipeline import IngestionPipeline
from app.ingest.store import VectorStore
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.vector import DenseRetriever
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel


@pytest.fixture
def client(memory_store: VectorStore, test_settings: Settings, tmp_path: Path) -> TestClient:
    settings = test_settings.model_copy(update={"data_dir": tmp_path / "data"})
    pipeline = IngestionPipeline(memory_store.embeddings, memory_store, settings=settings)
    retriever = HybridRetriever(
        DenseRetriever(memory_store),
        BM25Retriever(index=pipeline.bm25),
        default_mode="bm25",
        top_k=3,
    )
    state = AppState(settings, memory_store.embeddings, memory_store, pipeline, retriever)
    state._llm = FakeListChatModel(
        responses=["The warranty is 24 months [1].\nCONFIDENCE: 0.9"] * 5
    )
    with TestClient(create_app(state)) as c:
        yield c


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.replace("\r\n", "\n").strip().split("\n\n"):
        event, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        if event:
            events.append((event, data))
    return events


def test_health_empty(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["qdrant_reachable"] is True and body["documents"] == 0
    assert client.get("/documents").json() == []


def test_chat_without_documents_is_409(client: TestClient) -> None:
    r = client.post("/chat", json={"question": "anything"})
    assert r.status_code == 409


def test_upload_list_chat_delete(client: TestClient, txt_file: Path, docx_file: Path) -> None:
    with txt_file.open("rb") as f1, docx_file.open("rb") as f2:
        r = client.post(
            "/documents",
            files=[("files", (txt_file.name, f1, "text/plain")), ("files", (docx_file.name, f2))],
        )
    assert r.status_code == 201, r.text
    docs = r.json()
    assert {d["filename"] for d in docs} == {"warranty.txt", "vertrag.docx"}
    assert all(d["num_chunks"] > 0 for d in docs)
    assert len(client.get("/documents").json()) == 2

    # re-uploading the identical file is a no-op
    with txt_file.open("rb") as f1:
        r = client.post("/documents", files=[("files", (txt_file.name, f1))])
    assert r.status_code == 201 and len(client.get("/documents").json()) == 2

    # chat streams tokens and a final structured answer
    with client.stream(
        "POST", "/chat", json={"question": "How long is the warranty?", "retrieval_mode": "bm25"}
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        events = _parse_sse("".join(resp.iter_text()))
    kinds = [e for e, _ in events]
    assert kinds[0] == "token" and kinds[-1] == "final" and "error" not in kinds
    final = events[-1][1]
    assert final["answer_found"] is True
    assert final["citations"][0]["document_name"] == "warranty.txt"
    assert "".join(d["text"] for e, d in events if e == "token").strip() == final["answer"]
    assert final["retrieved"] and 0 < final["confidence"] <= 1

    # delete removes vectors, bm25 entries and the manifest entry
    txt_id = next(d["id"] for d in docs if d["filename"] == "warranty.txt")
    assert client.delete(f"/documents/{txt_id}").status_code == 204
    assert client.delete(f"/documents/{txt_id}").status_code == 404
    remaining = client.get("/documents").json()
    assert [d["filename"] for d in remaining] == ["vertrag.docx"]
    assert client.get("/health").json()["documents"] == 1


def test_upload_rejects_unsupported_type(client: TestClient) -> None:
    r = client.post("/documents", files=[("files", ("photo.png", b"\x89PNG", "image/png"))])
    assert r.status_code == 400
    assert "Unsupported" in r.json()["detail"]


def test_replacing_a_file_with_new_content_removes_old_version(
    client: TestClient, txt_file: Path
) -> None:
    with txt_file.open("rb") as f:
        first = client.post("/documents", files=[("files", ("policy.txt", f))]).json()[0]
    second = client.post(
        "/documents", files=[("files", ("policy.txt", b"# 1. New\nCompletely new content here."))]
    ).json()[0]
    assert first["id"] != second["id"]
    ids = [d["id"] for d in client.get("/documents").json()]
    assert ids == [second["id"]]


def test_clear_session(client: TestClient) -> None:
    assert client.delete("/sessions/abc").status_code == 204
