"""
Perpee RAG module.

Provides semantic search capabilities for product discovery using
ChromaDB and OpenAI embeddings.

Main components:
- RAGService: ChromaDB client and collection management
- EmbeddingService: OpenAI text-embedding-3-small integration
- ProductSearchService: Semantic and hybrid search
- IndexSyncService: Keep ChromaDB in sync with SQLite
"""

from .embeddings import (
    BatchEmbeddingResult,
    EmbeddingResult,
    EmbeddingService,
    create_product_document,
    create_product_metadata,
    get_embedding_service,
    reset_embedding_service,
)
from .search import (
    ProductSearchService,
    SearchOptions,
    SearchResult,
    get_search_service,
    reset_search_service,
)
from .service import (
    RAGService,
    get_rag_service,
    reset_rag_service,
)
from .sync import (
    IndexSyncService,
    SyncResult,
    get_sync_service,
    reset_sync_service,
)

__all__ = [
    # Service
    "RAGService",
    "get_rag_service",
    "reset_rag_service",
    # Embeddings
    "EmbeddingService",
    "EmbeddingResult",
    "BatchEmbeddingResult",
    "create_product_document",
    "create_product_metadata",
    "get_embedding_service",
    "reset_embedding_service",
    # Search
    "ProductSearchService",
    "SearchOptions",
    "SearchResult",
    "get_search_service",
    "reset_search_service",
    # Sync
    "IndexSyncService",
    "SyncResult",
    "get_sync_service",
    "reset_sync_service",
]
