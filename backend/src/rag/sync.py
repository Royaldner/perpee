"""
Index synchronization module for Perpee RAG system.
Keeps ChromaDB in sync with SQLite product data.
"""

import logging
from dataclasses import dataclass

from src.database.models import Product

from .embeddings import (
    EmbeddingService,
    create_product_document,
    create_product_metadata,
    get_embedding_service,
)
from .service import RAGService, get_rag_service

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    product_id: int
    operation: str  # "add", "update", "delete", "re_embed"
    message: str = ""


class IndexSyncService:
    """
    Service for synchronizing product index between SQLite and ChromaDB.

    Handles:
    - Index on product create
    - Update metadata on price/stock change
    - Re-embed on name/description change
    - Remove from index on soft delete
    """

    def __init__(
        self,
        rag_service: RAGService | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        """
        Initialize sync service.

        Args:
            rag_service: RAG service instance
            embedding_service: Embedding service instance
        """
        self._rag_service = rag_service
        self._embedding_service = embedding_service

    @property
    def rag_service(self) -> RAGService:
        """Get RAG service, initializing if needed."""
        if self._rag_service is None:
            self._rag_service = get_rag_service()
        return self._rag_service

    @property
    def embedding_service(self) -> EmbeddingService:
        """Get embedding service, initializing if needed."""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    async def index_product(self, product: Product) -> SyncResult:
        """
        Add a new product to the index.

        Args:
            product: Product to index

        Returns:
            SyncResult
        """
        try:
            # Create document for embedding
            document = create_product_document(
                name=product.name,
                brand=product.brand,
                store=product.store_domain,
                price=product.current_price,
                currency=product.currency,
            )

            # Generate embedding
            result = await self.embedding_service.embed_async(document)

            # Create metadata
            metadata = create_product_metadata(
                product_id=product.id,
                name=product.name,
                store_domain=product.store_domain,
                current_price=product.current_price,
                in_stock=product.in_stock,
                brand=product.brand,
                upc=product.upc,
            )

            # Add to ChromaDB
            self.rag_service.add_product(
                product_id=product.id,
                embedding=result.embedding,
                metadata=metadata,
                document=document,
            )

            logger.info(f"Indexed product {product.id}: {product.name}")
            return SyncResult(
                success=True,
                product_id=product.id,
                operation="add",
                message=f"Product indexed with {result.tokens_used} tokens",
            )

        except Exception as e:
            logger.error(f"Failed to index product {product.id}: {e}")
            return SyncResult(
                success=False,
                product_id=product.id,
                operation="add",
                message=str(e),
            )

    async def update_metadata(
        self,
        product: Product,
        fields_changed: list[str] | None = None,
    ) -> SyncResult:
        """
        Update product metadata without re-embedding.

        Use for price/stock changes that don't affect semantic search.

        Args:
            product: Product with updated data
            fields_changed: List of changed field names

        Returns:
            SyncResult
        """
        try:
            # Check if this is a metadata-only change (price/stock) vs embedding change (name/brand)
            needs_reembed = False

            if fields_changed:
                embedding_fields = {"name", "brand", "store_domain"}
                needs_reembed = bool(set(fields_changed) & embedding_fields)

            if needs_reembed:
                return await self.reembed_product(product)

            # Update metadata only
            metadata = create_product_metadata(
                product_id=product.id,
                name=product.name,
                store_domain=product.store_domain,
                current_price=product.current_price,
                in_stock=product.in_stock,
                brand=product.brand,
                upc=product.upc,
            )

            self.rag_service.update_product(
                product_id=product.id,
                metadata=metadata,
            )

            logger.info(f"Updated metadata for product {product.id}")
            return SyncResult(
                success=True,
                product_id=product.id,
                operation="update",
                message="Metadata updated",
            )

        except Exception as e:
            logger.error(f"Failed to update metadata for product {product.id}: {e}")
            return SyncResult(
                success=False,
                product_id=product.id,
                operation="update",
                message=str(e),
            )

    async def reembed_product(self, product: Product) -> SyncResult:
        """
        Re-generate embedding for a product.

        Use when name, brand, or other semantic fields change.

        Args:
            product: Product to re-embed

        Returns:
            SyncResult
        """
        try:
            # Create new document
            document = create_product_document(
                name=product.name,
                brand=product.brand,
                store=product.store_domain,
                price=product.current_price,
                currency=product.currency,
            )

            # Generate new embedding
            result = await self.embedding_service.embed_async(document)

            # Create updated metadata
            metadata = create_product_metadata(
                product_id=product.id,
                name=product.name,
                store_domain=product.store_domain,
                current_price=product.current_price,
                in_stock=product.in_stock,
                brand=product.brand,
                upc=product.upc,
            )

            # Update in ChromaDB
            self.rag_service.update_product(
                product_id=product.id,
                embedding=result.embedding,
                metadata=metadata,
                document=document,
            )

            logger.info(f"Re-embedded product {product.id}: {product.name}")
            return SyncResult(
                success=True,
                product_id=product.id,
                operation="re_embed",
                message=f"Product re-embedded with {result.tokens_used} tokens",
            )

        except Exception as e:
            logger.error(f"Failed to re-embed product {product.id}: {e}")
            return SyncResult(
                success=False,
                product_id=product.id,
                operation="re_embed",
                message=str(e),
            )

    def remove_product(self, product_id: int) -> SyncResult:
        """
        Remove a product from the index.

        Use on soft delete.

        Args:
            product_id: ID of product to remove

        Returns:
            SyncResult
        """
        try:
            self.rag_service.delete_product(product_id)

            logger.info(f"Removed product {product_id} from index")
            return SyncResult(
                success=True,
                product_id=product_id,
                operation="delete",
                message="Product removed from index",
            )

        except Exception as e:
            logger.error(f"Failed to remove product {product_id}: {e}")
            return SyncResult(
                success=False,
                product_id=product_id,
                operation="delete",
                message=str(e),
            )

    async def sync_product(
        self,
        product: Product,
        is_new: bool = False,
        is_deleted: bool = False,
        fields_changed: list[str] | None = None,
    ) -> SyncResult:
        """
        Smart sync that determines the appropriate operation.

        Args:
            product: Product to sync
            is_new: True if this is a new product
            is_deleted: True if product was soft-deleted
            fields_changed: List of changed field names

        Returns:
            SyncResult
        """
        if is_deleted or product.deleted_at is not None:
            return self.remove_product(product.id)

        if is_new:
            return await self.index_product(product)

        # Determine if we need to re-embed
        if fields_changed:
            embedding_fields = {"name", "brand"}
            if set(fields_changed) & embedding_fields:
                return await self.reembed_product(product)

        # Default to metadata update
        return await self.update_metadata(product, fields_changed)

    async def bulk_index(self, products: list[Product]) -> list[SyncResult]:
        """
        Index multiple products.

        Args:
            products: Products to index

        Returns:
            List of SyncResults
        """
        if not products:
            return []

        results = []

        # Generate documents
        documents = [
            create_product_document(
                name=p.name,
                brand=p.brand,
                store=p.store_domain,
                price=p.current_price,
                currency=p.currency,
            )
            for p in products
        ]

        try:
            # Batch embed
            embed_result = await self.embedding_service.embed_batch_async(documents)

            # Add to ChromaDB
            for i, product in enumerate(products):
                try:
                    metadata = create_product_metadata(
                        product_id=product.id,
                        name=product.name,
                        store_domain=product.store_domain,
                        current_price=product.current_price,
                        in_stock=product.in_stock,
                        brand=product.brand,
                        upc=product.upc,
                    )

                    self.rag_service.add_product(
                        product_id=product.id,
                        embedding=embed_result.embeddings[i],
                        metadata=metadata,
                        document=documents[i],
                    )

                    results.append(
                        SyncResult(
                            success=True,
                            product_id=product.id,
                            operation="add",
                            message="Bulk indexed",
                        )
                    )
                except Exception as e:
                    results.append(
                        SyncResult(
                            success=False,
                            product_id=product.id,
                            operation="add",
                            message=str(e),
                        )
                    )

            logger.info(f"Bulk indexed {len(products)} products")

        except Exception as e:
            # If batch embedding fails, fall back to individual indexing
            logger.warning(f"Batch embedding failed, falling back to individual: {e}")
            for product in products:
                result = await self.index_product(product)
                results.append(result)

        return results

    def bulk_remove(self, product_ids: list[int]) -> list[SyncResult]:
        """
        Remove multiple products from the index.

        Args:
            product_ids: IDs of products to remove

        Returns:
            List of SyncResults
        """
        results = []

        for product_id in product_ids:
            result = self.remove_product(product_id)
            results.append(result)

        return results


# ===========================================
# Global Service Instance
# ===========================================

_sync_service: IndexSyncService | None = None


def get_sync_service() -> IndexSyncService:
    """Get the global sync service instance."""
    global _sync_service
    if _sync_service is None:
        _sync_service = IndexSyncService()
    return _sync_service


def reset_sync_service() -> None:
    """Reset the global sync service instance."""
    global _sync_service
    _sync_service = None
