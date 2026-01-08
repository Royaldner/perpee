"""
RAG Service for Perpee.
Manages ChromaDB client and product collection for semantic search.
"""

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import get_settings

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG Service for semantic product search.

    Features:
    - ChromaDB client management
    - Product collection with metadata
    - Embedding storage and retrieval
    """

    COLLECTION_NAME = "products"
    EMBEDDING_DIMENSION = 1536  # OpenAI text-embedding-3-small

    def __init__(
        self,
        persist_directory: str | None = None,
        in_memory: bool = False,
    ):
        """
        Initialize RAG service.

        Args:
            persist_directory: Path for persistent storage (uses settings default if None)
            in_memory: Use in-memory storage (for testing)
        """
        settings = get_settings()

        if in_memory:
            self._client = chromadb.Client()
            logger.info("Initialized in-memory ChromaDB client")
        else:
            persist_path = persist_directory or settings.chromadb_path
            # Ensure directory exists
            Path(persist_path).mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=persist_path,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            logger.info(f"Initialized persistent ChromaDB client at {persist_path}")

        self._collection = None
        self._initialize_collection()

    def _initialize_collection(self) -> None:
        """Initialize or get the products collection."""
        try:
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={
                    "description": "Product embeddings for semantic search",
                    "hnsw:space": "cosine",  # Use cosine similarity
                },
            )
            logger.info(
                f"Collection '{self.COLLECTION_NAME}' ready with "
                f"{self._collection.count()} documents"
            )
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise

    @property
    def collection(self) -> chromadb.Collection:
        """Get the products collection."""
        if self._collection is None:
            self._initialize_collection()
        return self._collection

    @property
    def client(self) -> chromadb.Client:
        """Get the ChromaDB client."""
        return self._client

    def add_product(
        self,
        product_id: int,
        embedding: list[float],
        metadata: dict[str, Any],
        document: str,
    ) -> None:
        """
        Add a product to the collection.

        Args:
            product_id: Product database ID
            embedding: Product embedding vector
            metadata: Product metadata (name, store, price, etc.)
            document: Text document used for embedding
        """
        doc_id = self._product_id_to_doc_id(product_id)

        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[self._sanitize_metadata(metadata)],
            documents=[document],
        )
        logger.debug(f"Added product {product_id} to collection")

    def update_product(
        self,
        product_id: int,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        document: str | None = None,
    ) -> None:
        """
        Update a product in the collection.

        Args:
            product_id: Product database ID
            embedding: New embedding (optional)
            metadata: New metadata (optional)
            document: New document text (optional)
        """
        doc_id = self._product_id_to_doc_id(product_id)

        update_kwargs: dict[str, Any] = {"ids": [doc_id]}

        if embedding is not None:
            update_kwargs["embeddings"] = [embedding]
        if metadata is not None:
            update_kwargs["metadatas"] = [self._sanitize_metadata(metadata)]
        if document is not None:
            update_kwargs["documents"] = [document]

        self.collection.update(**update_kwargs)
        logger.debug(f"Updated product {product_id} in collection")

    def delete_product(self, product_id: int) -> None:
        """
        Remove a product from the collection.

        Args:
            product_id: Product database ID
        """
        doc_id = self._product_id_to_doc_id(product_id)

        self.collection.delete(ids=[doc_id])
        logger.debug(f"Deleted product {product_id} from collection")

    def get_product(self, product_id: int) -> dict[str, Any] | None:
        """
        Get a product from the collection.

        Args:
            product_id: Product database ID

        Returns:
            Product data dict or None if not found
        """
        doc_id = self._product_id_to_doc_id(product_id)

        result = self.collection.get(
            ids=[doc_id],
            include=["embeddings", "metadatas", "documents"],
        )

        if not result["ids"]:
            return None

        return {
            "id": product_id,
            "embedding": result["embeddings"][0] if result["embeddings"] is not None else None,
            "metadata": result["metadatas"][0] if result["metadatas"] is not None else None,
            "document": result["documents"][0] if result["documents"] is not None else None,
        }

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query similar products.

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Metadata filter
            where_document: Document content filter

        Returns:
            List of matching products with scores
        """
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["metadatas", "documents", "distances"],
        }

        if where:
            query_kwargs["where"] = where
        if where_document:
            query_kwargs["where_document"] = where_document

        results = self.collection.query(**query_kwargs)

        # Format results
        products = []
        for i, doc_id in enumerate(results["ids"][0]):
            product_id = self._doc_id_to_product_id(doc_id)
            products.append({
                "product_id": product_id,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else None,
                "document": results["documents"][0][i] if results["documents"] else None,
                "distance": results["distances"][0][i] if results["distances"] else None,
                "score": 1 - results["distances"][0][i] if results["distances"] else None,
            })

        return products

    def count(self) -> int:
        """Get the number of products in the collection."""
        return self.collection.count()

    def reset(self) -> None:
        """
        Reset the collection (delete all data).
        Use with caution!
        """
        self._client.delete_collection(self.COLLECTION_NAME)
        self._initialize_collection()
        logger.warning("Collection reset - all data deleted")

    def _product_id_to_doc_id(self, product_id: int) -> str:
        """Convert product ID to ChromaDB document ID."""
        return f"product_{product_id}"

    def _doc_id_to_product_id(self, doc_id: str) -> int:
        """Convert ChromaDB document ID to product ID."""
        return int(doc_id.replace("product_", ""))

    def _sanitize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize metadata for ChromaDB.
        ChromaDB only supports str, int, float, bool values.
        """
        sanitized = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            else:
                # Convert to string
                sanitized[key] = str(value)
        return sanitized


# ===========================================
# Global Service Instance
# ===========================================

_rag_service: RAGService | None = None


def get_rag_service(in_memory: bool = False) -> RAGService:
    """Get the global RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(in_memory=in_memory)
    return _rag_service


def reset_rag_service() -> None:
    """Reset the global RAG service instance."""
    global _rag_service
    _rag_service = None
