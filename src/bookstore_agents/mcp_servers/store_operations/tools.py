from typing import Any

from fastmcp import FastMCP

from bookstore_agents.common.observability import trace_mcp_tool
from bookstore_agents.mcp_servers.store_operations.repository import StoreOperationsRepository


def register_tools(mcp: FastMCP) -> None:
    repository = StoreOperationsRepository()

    @mcp.tool
    @trace_mcp_tool("store_operations", "check_stock")
    def check_stock(book_id: int | None = None, title: str | None = None) -> list[dict[str, Any]]:
        """Check stock availability by book ID or title."""
        return repository.check_stock(book_id, title)

    @mcp.tool
    @trace_mcp_tool("store_operations", "list_low_stock")
    def list_low_stock(threshold: int = 2) -> list[dict[str, Any]]:
        """List books with available stock at or below a threshold."""
        return repository.list_low_stock(threshold)

    @mcp.tool
    @trace_mcp_tool("store_operations", "create_reservation")
    def create_reservation(
        book_id: int,
        customer_id: int,
        pickup_date: str | None = None,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a pickup reservation after human approval."""
        return repository.create_reservation(book_id, customer_id, pickup_date, approval_id)

    @mcp.tool
    @trace_mcp_tool("store_operations", "cancel_reservation")
    def cancel_reservation(reservation_id: str, approval_id: str | None = None) -> dict[str, Any]:
        """Cancel an active reservation after human approval."""
        return repository.cancel_reservation(reservation_id, approval_id)

    @mcp.tool
    @trace_mcp_tool("store_operations", "mark_reservation_picked_up")
    def mark_reservation_picked_up(
        reservation_id: str,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        """Mark an active reservation as picked up after human approval."""
        return repository.mark_reservation_picked_up(reservation_id, approval_id)

    @mcp.tool
    @trace_mcp_tool("store_operations", "adjust_inventory")
    def adjust_inventory(
        book_id: int,
        quantity_delta: int,
        reason: str,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        """Adjust inventory after human approval."""
        return repository.adjust_inventory(book_id, quantity_delta, reason, approval_id)

    @mcp.tool
    @trace_mcp_tool("store_operations", "list_today_pickups")
    def list_today_pickups() -> list[dict[str, Any]]:
        """List reservations scheduled for pickup today."""
        return repository.list_today_pickups()

    @mcp.tool
    @trace_mcp_tool("store_operations", "daily_sales_summary")
    def daily_sales_summary(sale_date: str | None = None) -> dict[str, Any]:
        """Summarize sales for a date, defaulting to today."""
        return repository.daily_sales_summary(sale_date)

    @mcp.tool
    @trace_mcp_tool("store_operations", "top_selling_books")
    def top_selling_books(days: int = 7, limit: int = 5) -> list[dict[str, Any]]:
        """Return top-selling books for a recent date window."""
        return repository.top_selling_books(days, limit)
