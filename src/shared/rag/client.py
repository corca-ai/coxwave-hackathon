"""Qdrant vector database client for RAG."""

import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from shared.rag.schemas import VectorDocument, SearchResult


def _arxiv_id_to_point_id(arxiv_id: str) -> int:
    """Convert arxiv_id to numeric point ID for Qdrant."""
    hash_bytes = hashlib.md5(arxiv_id.encode()).digest()
    return int.from_bytes(hash_bytes[:8], byteorder="big") & 0x7FFFFFFFFFFFFFFF


class QdrantRAG:
    """Qdrant client for RAG operations."""

    def __init__(self, url: str, collection: str):
        """Initialize Qdrant client.

        Args:
            url: Qdrant server URL
            collection: Collection name
        """
        self.client = QdrantClient(url=url, check_compatibility=False)
        self.collection = collection

    def upsert(self, doc: VectorDocument, embedding: list[float]) -> None:
        """Store document with embedding.

        Args:
            doc: Document to store
            embedding: Document embedding vector
        """
        point_id = _arxiv_id_to_point_id(doc.arxiv_id)
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=doc.model_dump(),
        )
        self.client.upsert(
            collection_name=self.collection,
            points=[point],
        )

    def get_by_id(self, arxiv_id: str) -> VectorDocument | None:
        """Get document by arxiv_id.

        Args:
            arxiv_id: ArXiv paper ID

        Returns:
            Document if found, None otherwise
        """
        point_id = _arxiv_id_to_point_id(arxiv_id)
        results = self.client.retrieve(
            collection_name=self.collection,
            ids=[point_id],
            with_payload=True,
        )
        if not results:
            return None
        payload = results[0].payload
        return VectorDocument(**payload)

    def get_by_ids(self, arxiv_ids: list[str]) -> list[VectorDocument]:
        """Get multiple documents by arxiv_ids.

        Args:
            arxiv_ids: List of ArXiv paper IDs

        Returns:
            List of found documents
        """
        if not arxiv_ids:
            return []
        point_ids = [_arxiv_id_to_point_id(aid) for aid in arxiv_ids]
        results = self.client.retrieve(
            collection_name=self.collection,
            ids=point_ids,
            with_payload=True,
        )
        return [VectorDocument(**r.payload) for r in results if r.payload]

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> list[SearchResult]:
        """Search for similar documents.

        Args:
            query_embedding: Query vector
            top_k: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of similar documents with scores
        """
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_embedding,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [
            SearchResult(
                arxiv_id=r.payload["arxiv_id"],
                title=r.payload["title"],
                abstract=r.payload["abstract"],
                url=r.payload["url"],
                score=r.score,
            )
            for r in response.points
            if r.payload
        ]

    def exists(self, arxiv_id: str) -> bool:
        """Check if document exists.

        Args:
            arxiv_id: ArXiv paper ID

        Returns:
            True if exists
        """
        point_id = _arxiv_id_to_point_id(arxiv_id)
        results = self.client.retrieve(
            collection_name=self.collection,
            ids=[point_id],
        )
        return len(results) > 0
