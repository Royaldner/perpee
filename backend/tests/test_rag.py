"""
Tests for RAG system components.
Tests embedding generation, semantic search, and index sync operations.
"""

import pytest

from src.core.exceptions import EmbeddingError
from src.rag.embeddings import (
    EmbeddingService,
    create_product_document,
    create_product_metadata,
)
from src.rag.search import ProductSearchService, SearchOptions, SearchResult
from src.rag.service import RAGService
from src.rag.sync import IndexSyncService, SyncResult

# ===========================================
# Fixtures
# ===========================================


@pytest.fixture
def rag_service():
    """Create a fresh RAGService with clean collection for each test."""
    service = RAGService(in_memory=True)
    # Reset collection to ensure clean state
    service.reset()
    yield service


# ===========================================
# RAGService Tests
# ===========================================


class TestRAGService:
    """Tests for RAGService."""

    def test_init_in_memory(self, rag_service):
        """Test in-memory initialization."""
        assert rag_service.collection is not None
        assert rag_service.count() == 0

    def test_add_product(self, rag_service):
        """Test adding a product to collection."""
        # Create fake embedding (1536 dimensions)
        embedding = [0.1] * 1536
        metadata = {"name": "Test Product", "store_domain": "amazon.ca"}

        rag_service.add_product(
            product_id=1,
            embedding=embedding,
            metadata=metadata,
            document="Test Product | Store: amazon.ca",
        )

        assert rag_service.count() == 1

    def test_get_product(self, rag_service):
        """Test getting a product from collection."""
        embedding = [0.1] * 1536
        metadata = {"name": "Test Product", "store_domain": "amazon.ca"}

        rag_service.add_product(
            product_id=1,
            embedding=embedding,
            metadata=metadata,
            document="Test Product",
        )

        result = rag_service.get_product(1)
        assert result is not None
        assert result["id"] == 1
        assert result["metadata"]["name"] == "Test Product"

    def test_get_product_not_found(self, rag_service):
        """Test getting non-existent product."""
        result = rag_service.get_product(999)
        assert result is None

    def test_update_product(self, rag_service):
        """Test updating a product."""
        embedding = [0.1] * 1536
        metadata = {"name": "Test Product", "current_price": 10.0}

        rag_service.add_product(
            product_id=1,
            embedding=embedding,
            metadata=metadata,
            document="Test Product",
        )

        # Update metadata
        rag_service.update_product(
            product_id=1,
            metadata={"name": "Test Product", "current_price": 15.0},
        )

        result = rag_service.get_product(1)
        assert result["metadata"]["current_price"] == 15.0

    def test_delete_product(self, rag_service):
        """Test deleting a product."""
        embedding = [0.1] * 1536
        rag_service.add_product(
            product_id=1,
            embedding=embedding,
            metadata={"name": "Test"},
            document="Test",
        )

        assert rag_service.count() == 1

        rag_service.delete_product(1)
        assert rag_service.count() == 0

    def test_query(self, rag_service):
        """Test querying products."""
        # Add multiple products
        for i in range(5):
            embedding = [0.1 * (i + 1)] * 1536
            rag_service.add_product(
                product_id=i,
                embedding=embedding,
                metadata={"name": f"Product {i}", "store_domain": "amazon.ca"},
                document=f"Product {i}",
            )

        # Query
        query_embedding = [0.1] * 1536
        results = rag_service.query(query_embedding, n_results=3)

        assert len(results) == 3
        assert all("product_id" in r for r in results)
        assert all("score" in r for r in results)

    def test_query_with_filter(self, rag_service):
        """Test querying with metadata filter."""
        # Add products from different stores
        rag_service.add_product(
            product_id=1,
            embedding=[0.1] * 1536,
            metadata={"name": "Product 1", "store_domain": "amazon.ca"},
            document="Product 1",
        )
        rag_service.add_product(
            product_id=2,
            embedding=[0.2] * 1536,
            metadata={"name": "Product 2", "store_domain": "walmart.ca"},
            document="Product 2",
        )

        # Query with filter
        results = rag_service.query(
            query_embedding=[0.15] * 1536,
            n_results=10,
            where={"store_domain": {"$eq": "amazon.ca"}},
        )

        assert len(results) == 1
        assert results[0]["metadata"]["store_domain"] == "amazon.ca"

    def test_reset(self, rag_service):
        """Test resetting the collection."""
        rag_service.add_product(
            product_id=1,
            embedding=[0.1] * 1536,
            metadata={"name": "Test"},
            document="Test",
        )

        assert rag_service.count() == 1

        rag_service.reset()
        assert rag_service.count() == 0

    def test_sanitize_metadata(self, rag_service):
        """Test metadata sanitization."""
        metadata = {
            "name": "Test",
            "price": 10.5,
            "in_stock": True,
            "count": 5,
            "none_value": None,
            "complex": {"nested": "value"},
        }

        sanitized = rag_service._sanitize_metadata(metadata)

        assert sanitized["name"] == "Test"
        assert sanitized["price"] == 10.5
        assert sanitized["in_stock"] is True
        assert sanitized["count"] == 5
        assert "none_value" not in sanitized
        assert sanitized["complex"] == "{'nested': 'value'}"  # Converted to string


# ===========================================
# Embedding Tests
# ===========================================


class TestCreateProductDocument:
    """Tests for create_product_document helper."""

    def test_basic_document(self):
        """Test basic document creation."""
        doc = create_product_document(name="Test Product")
        assert "Test Product" in doc

    def test_full_document(self):
        """Test document with all fields."""
        doc = create_product_document(
            name="iPhone 15",
            brand="Apple",
            store="amazon.ca",
            price=1299.99,
            currency="CAD",
        )

        assert "iPhone 15" in doc
        assert "Brand: Apple" in doc
        assert "Store: amazon.ca" in doc
        assert "Price: CAD 1299.99" in doc


class TestCreateProductMetadata:
    """Tests for create_product_metadata helper."""

    def test_basic_metadata(self):
        """Test basic metadata creation."""
        metadata = create_product_metadata(
            product_id=1,
            name="Test Product",
            store_domain="amazon.ca",
        )

        assert metadata["product_id"] == 1
        assert metadata["name"] == "Test Product"
        assert metadata["store_domain"] == "amazon.ca"
        assert metadata["in_stock"] is True  # Default

    def test_full_metadata(self):
        """Test metadata with all fields."""
        metadata = create_product_metadata(
            product_id=1,
            name="Test Product",
            store_domain="amazon.ca",
            current_price=99.99,
            in_stock=False,
            brand="Test Brand",
            upc="123456789",
        )

        assert metadata["current_price"] == 99.99
        assert metadata["in_stock"] is False
        assert metadata["brand"] == "Test Brand"
        assert metadata["upc"] == "123456789"


class TestEmbeddingService:
    """Tests for EmbeddingService."""

    def test_embed_empty_text_raises_error(self):
        """Test that empty text raises EmbeddingError."""
        service = EmbeddingService(api_key="fake-key")

        with pytest.raises(EmbeddingError):
            service.embed("")

        with pytest.raises(EmbeddingError):
            service.embed("   ")

    def test_embed_batch_empty_raises_error(self):
        """Test that empty batch raises EmbeddingError."""
        service = EmbeddingService(api_key="fake-key")

        with pytest.raises(EmbeddingError):
            service.embed_batch([])

        with pytest.raises(EmbeddingError):
            service.embed_batch(["", "   "])

    @pytest.mark.asyncio
    async def test_embed_async_empty_raises_error(self):
        """Test that empty text raises EmbeddingError async."""
        service = EmbeddingService(api_key="fake-key")

        with pytest.raises(EmbeddingError):
            await service.embed_async("")


# ===========================================
# Search Tests
# ===========================================


class TestSearchOptions:
    """Tests for SearchOptions."""

    def test_default_options(self):
        """Test default search options."""
        options = SearchOptions()
        assert options.limit == 10
        assert options.store_domain is None
        assert options.in_stock_only is False

    def test_custom_options(self):
        """Test custom search options."""
        options = SearchOptions(
            limit=5,
            store_domain="amazon.ca",
            min_price=10.0,
            max_price=100.0,
            in_stock_only=True,
        )

        assert options.limit == 5
        assert options.store_domain == "amazon.ca"
        assert options.min_price == 10.0
        assert options.max_price == 100.0
        assert options.in_stock_only is True


class TestSearchResult:
    """Tests for SearchResult."""

    def test_search_result_creation(self):
        """Test SearchResult creation."""
        result = SearchResult(
            product_id=1,
            name="Test Product",
            store_domain="amazon.ca",
            current_price=99.99,
            in_stock=True,
            score=0.95,
            source="semantic",
        )

        assert result.product_id == 1
        assert result.name == "Test Product"
        assert result.score == 0.95
        assert result.source == "semantic"


class TestProductSearchService:
    """Tests for ProductSearchService."""

    def test_build_where_filter_empty(self):
        """Test where filter with no options."""
        service = ProductSearchService()
        options = SearchOptions()

        filter_result = service._build_where_filter(options)
        assert filter_result is None

    def test_build_where_filter_single(self):
        """Test where filter with single option."""
        service = ProductSearchService()
        options = SearchOptions(store_domain="amazon.ca")

        filter_result = service._build_where_filter(options)
        assert filter_result == {"store_domain": {"$eq": "amazon.ca"}}

    def test_build_where_filter_multiple(self):
        """Test where filter with multiple options."""
        service = ProductSearchService()
        options = SearchOptions(
            store_domain="amazon.ca",
            in_stock_only=True,
            min_price=10.0,
        )

        filter_result = service._build_where_filter(options)
        assert "$and" in filter_result
        assert len(filter_result["$and"]) == 3

    def test_merge_results(self):
        """Test merging semantic and SQLite results."""
        service = ProductSearchService()

        semantic = [
            SearchResult(1, "Product 1", "amazon.ca", 10.0, True, 0.9, "semantic"),
            SearchResult(2, "Product 2", "amazon.ca", 20.0, True, 0.8, "semantic"),
        ]

        sqlite = [
            SearchResult(2, "Product 2", "amazon.ca", 20.0, True, None, "sqlite"),
            SearchResult(3, "Product 3", "amazon.ca", 30.0, True, None, "sqlite"),
        ]

        merged = service._merge_results(semantic, sqlite, limit=5)

        # Should have 3 unique products
        assert len(merged) == 3
        # First two should be from semantic
        assert merged[0].product_id == 1
        assert merged[1].product_id == 2
        # Third should be from SQLite (now marked hybrid)
        assert merged[2].product_id == 3

    def test_merge_results_respects_limit(self):
        """Test that merge respects limit."""
        service = ProductSearchService()

        semantic = [
            SearchResult(i, f"Product {i}", "amazon.ca", 10.0, True, 0.9, "semantic")
            for i in range(5)
        ]
        sqlite = [
            SearchResult(i + 5, f"Product {i + 5}", "amazon.ca", 10.0, True, None, "sqlite")
            for i in range(5)
        ]

        merged = service._merge_results(semantic, sqlite, limit=3)
        assert len(merged) == 3


# ===========================================
# Sync Tests
# ===========================================


class TestSyncResult:
    """Tests for SyncResult."""

    def test_sync_result_creation(self):
        """Test SyncResult creation."""
        result = SyncResult(
            success=True,
            product_id=1,
            operation="add",
            message="Product indexed",
        )

        assert result.success is True
        assert result.product_id == 1
        assert result.operation == "add"
        assert result.message == "Product indexed"


class TestIndexSyncService:
    """Tests for IndexSyncService."""

    def test_remove_product(self, rag_service):
        """Test removing a product from index."""
        # Add a product
        rag_service.add_product(
            product_id=1,
            embedding=[0.1] * 1536,
            metadata={"name": "Test"},
            document="Test",
        )

        assert rag_service.count() == 1

        # Create sync service and remove
        sync_service = IndexSyncService(rag_service=rag_service)
        result = sync_service.remove_product(1)

        assert result.success is True
        assert result.operation == "delete"
        assert rag_service.count() == 0

    def test_bulk_remove(self, rag_service):
        """Test bulk removing products."""
        # Add products
        for i in range(5):
            rag_service.add_product(
                product_id=i,
                embedding=[0.1] * 1536,
                metadata={"name": f"Test {i}"},
                document=f"Test {i}",
            )

        assert rag_service.count() == 5

        sync_service = IndexSyncService(rag_service=rag_service)
        results = sync_service.bulk_remove([0, 1, 2])

        assert len(results) == 3
        assert all(r.success for r in results)
        assert rag_service.count() == 2


# ===========================================
# Integration Tests
# ===========================================


class TestRAGIntegration:
    """Integration tests for RAG system."""

    def test_add_query_delete_flow(self, rag_service):
        """Test full add-query-delete workflow."""
        # Add products
        products = [
            ("iPhone 15 Pro", "Apple", "amazon.ca"),
            ("Samsung Galaxy S24", "Samsung", "bestbuy.ca"),
            ("Google Pixel 8", "Google", "walmart.ca"),
        ]

        for i, (name, brand, store) in enumerate(products):
            doc = create_product_document(name=name, brand=brand, store=store)
            # Simple embedding based on index for testing
            embedding = [0.1 * (i + 1)] * 1536

            rag_service.add_product(
                product_id=i,
                embedding=embedding,
                metadata=create_product_metadata(
                    product_id=i,
                    name=name,
                    store_domain=store,
                    brand=brand,
                ),
                document=doc,
            )

        assert rag_service.count() == 3

        # Query
        results = rag_service.query(
            query_embedding=[0.1] * 1536,
            n_results=2,
        )
        assert len(results) == 2

        # Delete one
        rag_service.delete_product(0)
        assert rag_service.count() == 2

        # Verify deleted product not in results
        results = rag_service.query(
            query_embedding=[0.1] * 1536,
            n_results=10,
        )
        product_ids = [r["product_id"] for r in results]
        assert 0 not in product_ids

    def test_metadata_filter_integration(self, rag_service):
        """Test metadata filtering in queries."""
        # Add products with different prices and stock status
        test_data = [
            (1, "Cheap In Stock", 10.0, True),
            (2, "Expensive In Stock", 100.0, True),
            (3, "Cheap Out of Stock", 15.0, False),
            (4, "Mid Price In Stock", 50.0, True),
        ]

        for pid, name, price, in_stock in test_data:
            rag_service.add_product(
                product_id=pid,
                embedding=[0.1] * 1536,
                metadata={
                    "name": name,
                    "current_price": price,
                    "in_stock": in_stock,
                    "store_domain": "amazon.ca",
                },
                document=name,
            )

        # Query only in-stock products
        results = rag_service.query(
            query_embedding=[0.1] * 1536,
            n_results=10,
            where={"in_stock": {"$eq": True}},
        )

        assert len(results) == 3
        for r in results:
            assert r["metadata"]["in_stock"] is True
