"""Ingestion pipeline: parse -> chunk -> embed -> Qdrant + BM25, tracked in a manifest.

Re-ingesting the same file is a no-op because the document id is the SHA-256 of the file
content. Changing a file gives a new id, so the old version must be deleted explicitly
(the API does that when a file with the same name is uploaded again).

CLI:  python -m app.ingest.pipeline data/sample_docs [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.embeddings import Embeddings

from app.config import Settings, get_settings
from app.ingest.bm25_index import BM25Index
from app.ingest.chunking import chunk_document, detect_language
from app.ingest.parsers import SUPPORTED_EXTENSIONS, parse_file
from app.ingest.store import VectorStore
from app.schemas import DocumentInfo

logger = logging.getLogger(__name__)


def compute_document_id(data: bytes) -> str:
    """Stable document id: first 16 hex chars of the SHA-256 of the file bytes."""
    return hashlib.sha256(data).hexdigest()[:16]


class Manifest:
    """JSON file listing every ingested document; the source of truth for GET /documents."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.documents: dict[str, DocumentInfo] = {}
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.documents = {k: DocumentInfo.model_validate(v) for k, v in raw.items()}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.model_dump(mode="json") for k, v in self.documents.items()}
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def by_filename(self, filename: str) -> DocumentInfo | None:
        return next((d for d in self.documents.values() if d.filename == filename), None)


class IngestionPipeline:
    """Coordinates parsing, chunking, embedding and indexing."""

    def __init__(
        self,
        embeddings: Embeddings,
        vector_store: VectorStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embeddings = embeddings
        self.vector_store = vector_store or VectorStore(embeddings, settings=self.settings)
        self.bm25 = BM25Index.load(self.settings.bm25_index_path)
        self.manifest = Manifest(self.settings.index_dir / "manifest.json")

    def ingest_file(self, path: Path, force: bool = False) -> DocumentInfo:
        """Ingest one file. Returns its DocumentInfo; skips work if already ingested."""
        data = path.read_bytes()
        document_id = compute_document_id(data)
        existing = self.manifest.documents.get(document_id)
        if existing and not force:
            logger.info("skip %s: already ingested as %s", path.name, document_id)
            return existing

        parsed = parse_file(path)
        chunks = chunk_document(
            parsed,
            document_id=document_id,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        if not chunks:
            raise ValueError(f"{path.name} contains no extractable text")

        if existing:  # force re-ingest: drop the old vectors first
            self.vector_store.delete_document(document_id)
        self.vector_store.upsert_chunks(chunks, batch_size=self.settings.embed_batch_size)
        self.bm25.add(chunks)
        self.bm25.save(self.settings.bm25_index_path)

        info = DocumentInfo(
            id=document_id,
            filename=path.name,
            file_type=parsed.file_type,
            language=detect_language(parsed.text),
            num_pages=parsed.num_pages,
            num_chunks=len(chunks),
            size_bytes=len(data),
            ingested_at=datetime.now(UTC),
        )
        self.manifest.documents[document_id] = info
        self.manifest.save()
        logger.info("ingested %s -> %d chunks (%s)", path.name, len(chunks), info.language)
        return info

    def ingest_directory(self, directory: Path, force: bool = False) -> list[DocumentInfo]:
        """Ingest every supported file in a directory (not recursive)."""
        files = sorted(p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
        if not files:
            logger.warning("no supported files in %s", directory)
        return [self.ingest_file(p, force=force) for p in files]

    def delete_document(self, document_id: str) -> bool:
        """Remove a document from Qdrant, BM25 and the manifest. Returns False if unknown."""
        if document_id not in self.manifest.documents:
            return False
        self.vector_store.delete_document(document_id)
        self.bm25.remove_document(document_id)
        self.bm25.save(self.settings.bm25_index_path)
        del self.manifest.documents[document_id]
        self.manifest.save()
        logger.info("deleted document %s", document_id)
        return True

    def list_documents(self) -> list[DocumentInfo]:
        return sorted(self.manifest.documents.values(), key=lambda d: d.filename.lower())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest documents into DocuMind.")
    parser.add_argument("path", type=Path, help="file or directory to ingest")
    parser.add_argument("--force", action="store_true", help="re-ingest even if unchanged")
    args = parser.parse_args(argv)

    from app.llm import get_embeddings  # imported here so --help works without providers

    settings = get_settings()
    pipeline = IngestionPipeline(get_embeddings(settings=settings), settings=settings)
    if args.path.is_dir():
        infos = pipeline.ingest_directory(args.path, force=args.force)
    else:
        infos = [pipeline.ingest_file(args.path, force=args.force)]

    width = max(len(i.filename) for i in infos) if infos else 10
    print(f"\n{'document':<{width}}  lang  pages  chunks")
    for info in infos:
        row = f"{info.filename:<{width}}  {info.language:<4}  {info.num_pages:>5}"
        print(f"{row}  {info.num_chunks:>6}")
    print(
        f"\n{len(infos)} documents, {sum(i.num_chunks for i in infos)} chunks total, "
        f"{pipeline.vector_store.count()} vectors in Qdrant, {len(pipeline.bm25)} in BM25"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
