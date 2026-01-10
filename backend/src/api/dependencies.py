"""
FastAPI dependencies for request handling.
"""

from src.database.session import get_session_dependency

# Re-export the session dependency for use in routes
get_db = get_session_dependency

__all__ = ["get_db"]
