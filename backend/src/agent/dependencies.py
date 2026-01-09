"""
Agent dependencies for service injection.
Provides database session, scraper engine, and RAG service to agent tools.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.rag.search import ProductSearchService
from src.rag.sync import IndexSyncService
from src.scraper.engine import ScraperEngine


@dataclass
class AgentDependencies:
    """
    Container for all dependencies needed by agent tools.

    This is passed to Pydantic AI as the deps type, allowing
    tools to access services without global state.
    """

    session: AsyncSession
    scraper: ScraperEngine
    search_service: ProductSearchService
    sync_service: IndexSyncService

    @classmethod
    def create(
        cls,
        session: AsyncSession,
        scraper: ScraperEngine | None = None,
        search_service: ProductSearchService | None = None,
        sync_service: IndexSyncService | None = None,
    ) -> "AgentDependencies":
        """
        Create dependencies with defaults for optional services.

        Args:
            session: Database session (required)
            scraper: Scraper engine (optional, uses global)
            search_service: Search service (optional, uses global)
            sync_service: Index sync service (optional, uses global)

        Returns:
            AgentDependencies instance
        """
        from src.rag.search import get_search_service
        from src.rag.sync import get_sync_service
        from src.scraper.engine import get_scraper_engine

        return cls(
            session=session,
            scraper=scraper or get_scraper_engine(),
            search_service=search_service or get_search_service(),
            sync_service=sync_service or get_sync_service(),
        )
