"""Qdrant vector store wrapper used by ingestion (upsert/delete) and retrieval (search)."""

from __future__ import annotations

import logging
import uuid

from langchain_core.embeddings import Embeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import Settings, get_settings
from app.schemas import Chunk

logger = logging.getLogger(__name__)

_NAMESPACE = uuid.UUID("6f1b2c7e-3d4a-4b5c-9e8f-0a1b2c3d4e5f")


def point_id(chunk_id: str) -> str:
    """Qdrant needs UUID or int ids; derive a stable UUID from our '<doc>:<index>' id."""
    return str(uuid.uuid5(_NAMESPACE, chunk_id))


def make_client(settings: Settings | None = None) -> QdrantClient:
    """Create a Qdrant client from settings."""
    settings = settings or get_settings()
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=30)


class VectorStore:
    """Thin layer over qdrant-client that speaks in Chunk objects."""

    def __init__(
        self,
        embeddings: Embeddings,
        client: QdrantClient | None = None,
        collection: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embeddings = embeddings
        self.client = client or make_client(self.settings)
        self.collection = collection or self.settings.qdrant_collection
        self._dimension: int | None = None

    # -- collection -----------------------------------------------------------
    @property
    def dimension(self) -> int:
        """Embedding size, discovered once by embedding a probe string."""
        if self._dimension is None:
            self._dimension = len(self.embeddings.embed_query("dimension probe"))
        return self._dimension

    def ensure_collection(self) -> None:
        """Create the collection and the document_id payload index if missing."""
        if self.client.collection_exists(self.collection):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qm.VectorParams(size=self.dimension, distance=qm.Distance.COSINE),
        )
        self.client.create_payload_index(
            collection_name=self.collection,
            field_name="document_id",
            field_schema=qm.PayloadSchemaType.KEYWORD,
        )
        logger.info("created Qdrant collection %s (dim=%d)", self.collection, self.dimension)

    def is_reachable(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:  # noqa: BLE001 - any transport error means "not reachable"
            return False

    # -- writes -----------------------------------------------------------------
    def upsert_chunks(self, chunks: list[Chunk], batch_size: int = 32) -> int:
        """Embed chunks in batches and upsert them. Returns the number of points written."""
        self.ensure_collection()
        written = 0
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            vectors = self.embeddings.embed_documents([c.text for c in batch])
            points = [
                qm.PointStruct(id=point_id(c.id), vector=v, payload=c.model_dump())
                for c, v in zip(batch, vectors, strict=True)
            ]
            self.client.upsert(collection_name=self.collection, points=points, wait=True)
            written += len(points)
            logger.debug("upserted %d/%d chunks", written, len(chunks))
        return written

    def delete_document(self, document_id: str) -> None:
        """Delete every point belonging to a document."""
        if not self.client.collection_exists(self.collection):
            return
        self.client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(filter=_document_filter(document_id)),
            wait=True,
        )

    # -- reads --------------------------------------------------------------------
    def count(self, document_id: str | None = None) -> int:
        if not self.client.collection_exists(self.collection):
            return 0
        flt = _document_filter(document_id) if document_id else None
        return self.client.count(self.collection, count_filter=flt, exact=True).count

    def all_chunks(self, page_size: int = 256) -> list[Chunk]:
        """Every stored chunk, read from the point payloads (no vectors, no embedding call).

        Used to rebuild the BM25 index and the manifest after the local disk was wiped.
        """
        if not self.client.collection_exists(self.collection):
            return []
        chunks: list[Chunk] = []
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection,
                limit=page_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            chunks.extend(Chunk.model_validate(p.payload) for p in points)
            if offset is None:
                return chunks

    def search(self, query: str, k: int = 10) -> list[tuple[Chunk, float]]:
        """Dense similarity search. Returns (chunk, cosine_similarity) pairs, best first."""
        if not self.client.collection_exists(self.collection):
            return []
        vector = self.embeddings.embed_query(query)
        result = self.client.query_points(
            collection_name=self.collection, query=vector, limit=k, with_payload=True
        )
        return [(Chunk.model_validate(p.payload), float(p.score)) for p in result.points]


def _document_filter(document_id: str) -> qm.Filter:
    return qm.Filter(
        must=[qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id))]
    )
