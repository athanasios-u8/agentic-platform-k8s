from typing import Any

from fastmcp import FastMCP

from bookstore_agents.mcp_servers.catalog.repository import CatalogRepository


def register_tools(mcp: FastMCP) -> None:
    repository = CatalogRepository()

    @mcp.tool
    def search_books(
        keyword: str | None = None,
        genre: str | None = None,
        max_price: float | None = None,
        audience: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search bookstore catalog by keyword, genre, price, or audience."""
        return repository.search_books(keyword, genre, max_price, audience, limit)

    @mcp.tool
    def get_book_details(book_id: int) -> dict[str, Any] | None:
        """Return detailed metadata and current availability for one book."""
        return repository.get_book_details(book_id)

    @mcp.tool
    def recommend_books(
        prompt: str,
        genre: str | None = None,
        max_price: float | None = None,
        audience: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Recommend books for a natural-language request and optional filters."""
        return repository.recommend_books(prompt, genre, max_price, audience, limit)
