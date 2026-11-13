"""Pipeline tests using in-memory Qdrant and deterministic fake embeddings."""

from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.ingest.bm25_index import BM25Index, tokenize
from app.ingest.pipeline import IngestionPipeline, compute_document_id
from app.ingest.store import VectorStore


def test_tokenize() -> None:
    assert tokenize("Die Gewährleistung: 24 Monate!") == ["gewährleistung", "24", "monate"]
    assert tokenize("How long is the warranty?") == ["warranty"]


def test_bm25_roundtrip(tmp_path: Path, txt_file: Path, test_settings: Settings) -> None:
    from app.ingest.chunking import chunk_document
    from app.ingest.parsers import parse_file

    chunks = chunk_document(parse_file(txt_file), "d1", 200, 40)
    index = BM25Index(chunks)
    hits = index.search("RMA number", k=3)
    assert hits and "RMA" in hits[0][0].text
    index.save(tmp_path / "bm25.pkl")
    loaded = BM25Index.load(tmp_path / "bm25.pkl")
    assert len(loaded) == len(chunks)
    assert loaded.remove_document("d1") == len(chunks)
    assert loaded.search("RMA", k=3) == []


def test_ingest_is_idempotent_and_deletable(
    txt_file: Path,
    docx_file: Path,
    pdf_file: Path,
    memory_store: VectorStore,
    test_settings: Settings,
) -> None:
    pipeline = IngestionPipeline(memory_store.embeddings, memory_store, settings=test_settings)
    infos = pipeline.ingest_directory(txt_file.parent)
    assert {i.file_type for i in infos} == {"txt", "docx", "pdf"}
    assert {i.language for i in infos} == {"en", "de"}
    total = sum(i.num_chunks for i in infos)
    assert memory_store.count() == total == len(pipeline.bm25)

    # second run: nothing new is written
    again = pipeline.ingest_directory(txt_file.parent)
    assert [a.id for a in again] == [i.id for i in infos]
    assert memory_store.count() == total

    # manifest persisted to disk and reloaded by a fresh pipeline
    fresh = IngestionPipeline(memory_store.embeddings, memory_store, settings=test_settings)
    assert len(fresh.list_documents()) == 3

    # delete one document everywhere
    pdf_info = next(i for i in infos if i.file_type == "pdf")
    assert fresh.delete_document(pdf_info.id) is True
    assert fresh.delete_document(pdf_info.id) is False
    assert memory_store.count(pdf_info.id) == 0
    assert memory_store.count() == total - pdf_info.num_chunks
    assert pdf_info.id not in fresh.bm25.document_ids


def test_document_id_is_content_hash(txt_file: Path) -> None:
    data = txt_file.read_bytes()
    assert compute_document_id(data) == compute_document_id(data)
    assert compute_document_id(data) != compute_document_id(data + b"x")
    assert len(compute_document_id(data)) == 16


def test_dense_search_returns_ingested_chunk(
    txt_file: Path, memory_store: VectorStore, test_settings: Settings
) -> None:
    pipeline = IngestionPipeline(memory_store.embeddings, memory_store, settings=test_settings)
    pipeline.ingest_file(txt_file)
    hits = memory_store.search("warranty", k=2)
    assert len(hits) == 2
    assert all(isinstance(score, float) for _, score in hits)


def test_restore_from_vector_store_after_disk_wipe(
    txt_file: Path,
    docx_file: Path,
    pdf_file: Path,
    memory_store: VectorStore,
    test_settings: Settings,
) -> None:
    """A host with an ephemeral disk loses data/index; Qdrant still has every chunk."""
    import shutil

    pipeline = IngestionPipeline(memory_store.embeddings, memory_store, settings=test_settings)
    infos = {i.id: i for i in pipeline.ingest_directory(txt_file.parent)}
    assert pipeline.restore_from_vector_store() == 0  # documents already known: no-op

    shutil.rmtree(test_settings.index_dir)  # simulate the restart
    wiped = IngestionPipeline(memory_store.embeddings, memory_store, settings=test_settings)
    assert wiped.list_documents() == [] and len(wiped.bm25) == 0
    bm25_before = wiped.bm25

    assert wiped.restore_from_vector_store() == 3
    assert wiped.bm25 is bm25_before  # mutated in place: retrievers keep their reference
    assert len(wiped.bm25) == memory_store.count()
    assert wiped.bm25.search("RMA number", k=3)
    for restored in wiped.list_documents():
        original = infos[restored.id]
        assert restored.filename == original.filename
        assert restored.file_type == original.file_type
        assert restored.language == original.language
        assert restored.num_chunks == original.num_chunks

    # both files are back on disk, so the next start loads them without touching Qdrant
    again = IngestionPipeline(memory_store.embeddings, memory_store, settings=test_settings)
    assert len(again.list_documents()) == 3 and len(again.bm25) == len(wiped.bm25)


def test_restore_with_empty_vector_store(
    memory_store: VectorStore, test_settings: Settings
) -> None:
    pipeline = IngestionPipeline(memory_store.embeddings, memory_store, settings=test_settings)
    assert pipeline.restore_from_vector_store() == 0
    assert pipeline.list_documents() == []
