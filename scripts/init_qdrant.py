#!/usr/bin/env python3
"""Initialize Qdrant collection for RAG."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

from shared.config import get_settings


def init_collection():
    """Create papers collection in Qdrant."""
    settings = get_settings()

    client = QdrantClient(url=settings.qdrant_url)

    # Check if collection exists
    collections = client.get_collections().collections
    if any(c.name == settings.qdrant_collection for c in collections):
        print(f"Collection '{settings.qdrant_collection}' already exists.")
        return

    # Create collection
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(
            size=settings.embedding_dim,
            distance=Distance.COSINE,
        ),
    )
    print(f"Created collection '{settings.qdrant_collection}'")


if __name__ == "__main__":
    init_collection()
