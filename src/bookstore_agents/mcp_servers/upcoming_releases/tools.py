from typing import Any

from fastmcp import FastMCP

from bookstore_agents.common.observability import trace_mcp_tool
from bookstore_agents.mcp_servers.upcoming_releases.repository import (
    UpcomingReleasesRepository,
)


def register_tools(mcp: FastMCP) -> None:
    repository = UpcomingReleasesRepository()

    @mcp.tool
    @trace_mcp_tool("upcoming_releases", "search_upcoming_book_releases")
    def search_upcoming_book_releases(
        query: str,
        author: str | None = None,
        theme: str | None = None,
        limit: int = 5,
        months_ahead: int = 12,
    ) -> dict[str, Any]:
        """Search the web for upcoming book releases by author, theme, or genre."""
        return repository.search_upcoming_book_releases(
            query=query,
            author=author,
            theme=theme,
            limit=limit,
            months_ahead=months_ahead,
        )
