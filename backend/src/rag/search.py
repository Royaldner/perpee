"""
Search module for Perpee RAG system.
Implements semantic search, hybrid search, and SQLite fallback.
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import SearchError
from src.database.models import Product

from .embeddings import EmbeddingService, get_embedding_service
from .service import RAGService, get_rag_service

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result of a product search."""

    product_id: int
    name: str
    store_domain: str
    current_price: float | None
    in_stock: bool
    score: float | None = None
    source: str = "semantic"  # "semantic", "hybrid", or "sqlite"


@dataclass
class SearchOptions:
    """Options for search queries."""

    limit: int = 10
    store_domain: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    in_stock_only: bool = False


class ProductSearchService:
    """
    Service for searching products using semantic and hybrid methods.

    Features:
    - Semantic search using ChromaDB embeddings
    - Hybrid search (embedding + SQLite enrichment)
    - Fallback to SQLite LIKE when ChromaDB unavailable
    """

    def __init__(
        self,
        rag_service: RAGService | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        """
        Initialize search service.

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

    async def search(
        self,
        query: str,
        session: AsyncSession,
        options: SearchOptions | None = None,
    ) -> list[SearchResult]:
        """
        Search for products using semantic search with SQLite fallback.

        Args:
            query: Search query
            session: Database session for SQLite fallback/enrichment
            options: Search options

        Returns:
            List of search results
        """
        options = options or SearchOptions()

        try:
            # Try semantic search first
            return await self._semantic_search(query, session, options)
        except Exception as e:
            logger.warning(f"Semantic search failed, falling back to SQLite: {e}")
            return await self._sqlite_fallback(query, session, options)

    async def _semantic_search(
        self,
        query: str,
        session: AsyncSession,
        options: SearchOptions,
    ) -> list[SearchResult]:
        """
        Perform semantic search using ChromaDB.

        Args:
            query: Search query
            session: Database session for enrichment
            options: Search options

        Returns:
            List of search results
        """
        # Generate query embedding
        try:
            result = await self.embedding_service.embed_async(query)
            query_embedding = result.embedding
        except Exception as e:
            raise SearchError(f"Failed to generate query embedding: {e}") from e

        # Build metadata filter
        where_filter = self._build_where_filter(options)

        # Query ChromaDB
        results = self.rag_service.query(
            query_embedding=query_embedding,
            n_results=options.limit,
            where=where_filter if where_filter else None,
        )

        # Enrich results with current data from SQLite
        return await self._enrich_results(results, session)

    async def hybrid_search(
        self,
        query: str,
        session: AsyncSession,
        options: SearchOptions | None = None,
    ) -> list[SearchResult]:
        """
        Hybrid search combining semantic and keyword matching.

        Performs both semantic search and keyword search, then merges
        and deduplicates results.

        Args:
            query: Search query
            session: Database session
            options: Search options

        Returns:
            List of search results
        """
        options = options or SearchOptions()

        # Run both searches
        semantic_results = []
        sqlite_results = []

        try:
            semantic_results = await self._semantic_search(query, session, options)
        except Exception as e:
            logger.warning(f"Semantic search in hybrid failed: {e}")

        sqlite_results = await self._sqlite_fallback(query, session, options)

        # Merge and deduplicate
        return self._merge_results(semantic_results, sqlite_results, options.limit)

    async def _sqlite_fallback(
        self,
        query: str,
        session: AsyncSession,
        options: SearchOptions,
    ) -> list[SearchResult]:
        """
        Fallback search using SQLite LIKE queries.

        Args:
            query: Search query
            session: Database session
            options: Search options

        Returns:
            List of search results
        """
        # Build query
        stmt = select(Product).where(Product.deleted_at.is_(None))

        # Search in name and brand
        search_pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(search_pattern),
                Product.brand.ilike(search_pattern),
            )
        )

        # Apply filters
        if options.store_domain:
            stmt = stmt.where(Product.store_domain == options.store_domain)
        if options.in_stock_only:
            stmt = stmt.where(Product.in_stock.is_(True))
        if options.min_price is not None:
            stmt = stmt.where(Product.current_price >= options.min_price)
        if options.max_price is not None:
            stmt = stmt.where(Product.current_price <= options.max_price)

        stmt = stmt.limit(options.limit)

        result = await session.execute(stmt)
        products = result.scalars().all()

        return [
            SearchResult(
                product_id=p.id,
                name=p.name,
                store_domain=p.store_domain,
                current_price=p.current_price,
                in_stock=p.in_stock,
                score=None,
                source="sqlite",
            )
            for p in products
        ]

    async def _enrich_results(
        self,
        chroma_results: list[dict[str, Any]],
        session: AsyncSession,
    ) -> list[SearchResult]:
        """
        Enrich ChromaDB results with current data from SQLite.

        Args:
            chroma_results: Results from ChromaDB query
            session: Database session

        Returns:
            Enriched search results
        """
        if not chroma_results:
            return []

        # Get product IDs
        product_ids = [r["product_id"] for r in chroma_results]

        # Fetch current product data
        stmt = select(Product).where(
            Product.id.in_(product_ids),
            Product.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        products = {p.id: p for p in result.scalars().all()}

        # Build enriched results
        results = []
        for chroma_result in chroma_results:
            product_id = chroma_result["product_id"]
            product = products.get(product_id)

            if product:
                results.append(
                    SearchResult(
                        product_id=product.id,
                        name=product.name,
                        store_domain=product.store_domain,
                        current_price=product.current_price,
                        in_stock=product.in_stock,
                        score=chroma_result.get("score"),
                        source="semantic",
                    )
                )
            else:
                # Product may have been deleted, use ChromaDB metadata
                metadata = chroma_result.get("metadata", {})
                results.append(
                    SearchResult(
                        product_id=product_id,
                        name=metadata.get("name", "Unknown"),
                        store_domain=metadata.get("store_domain", "Unknown"),
                        current_price=metadata.get("current_price"),
                        in_stock=metadata.get("in_stock", False),
                        score=chroma_result.get("score"),
                        source="semantic",
                    )
                )

        return results

    def _build_where_filter(self, options: SearchOptions) -> dict[str, Any] | None:
        """
        Build ChromaDB where filter from options.

        Args:
            options: Search options

        Returns:
            Where filter dict or None
        """
        conditions = []

        if options.store_domain:
            conditions.append({"store_domain": {"$eq": options.store_domain}})
        if options.in_stock_only:
            conditions.append({"in_stock": {"$eq": True}})
        if options.min_price is not None:
            conditions.append({"current_price": {"$gte": options.min_price}})
        if options.max_price is not None:
            conditions.append({"current_price": {"$lte": options.max_price}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    def _merge_results(
        self,
        semantic: list[SearchResult],
        sqlite: list[SearchResult],
        limit: int,
    ) -> list[SearchResult]:
        """
        Merge and deduplicate search results.

        Semantic results are prioritized, then SQLite results fill remaining slots.

        Args:
            semantic: Semantic search results
            sqlite: SQLite search results
            limit: Maximum number of results

        Returns:
            Merged results
        """
        seen_ids = set()
        merged = []

        # Add semantic results first (higher priority)
        for result in semantic:
            if result.product_id not in seen_ids:
                seen_ids.add(result.product_id)
                merged.append(result)
                if len(merged) >= limit:
                    return merged

        # Fill with SQLite results
        for result in sqlite:
            if result.product_id not in seen_ids:
                seen_ids.add(result.product_id)
                result.source = "hybrid"  # Mark as hybrid since it's a merge
                merged.append(result)
                if len(merged) >= limit:
                    return merged

        return merged


# ===========================================
# Global Service Instance
# ===========================================

_search_service: ProductSearchService | None = None


def get_search_service() -> ProductSearchService:
    """Get the global search service instance."""
    global _search_service
    if _search_service is None:
        _search_service = ProductSearchService()
    return _search_service


def reset_search_service() -> None:
    """Reset the global search service instance."""
    global _search_service
    _search_service = None
