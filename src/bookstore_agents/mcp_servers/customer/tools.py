from typing import Any

from fastmcp import FastMCP

from bookstore_agents.common.observability import trace_mcp_tool
from bookstore_agents.mcp_servers.customer.repository import CustomerRepository


def register_tools(mcp: FastMCP) -> None:
    repository = CustomerRepository()

    @mcp.tool
    @trace_mcp_tool("customer", "get_customer")
    def get_customer(
        customer_id: int | None = None, email: str | None = None
    ) -> dict[str, Any] | None:
        """Retrieve customer profile and reading preferences."""
        return repository.get_customer(customer_id, email)

    @mcp.tool
    @trace_mcp_tool("customer", "lookup_loyalty_status")
    def lookup_loyalty_status(customer_id: int) -> dict[str, Any] | None:
        """Check loyalty tier and benefits for a customer."""
        return repository.lookup_loyalty_status(customer_id)

    @mcp.tool
    @trace_mcp_tool("customer", "update_customer_preferences")
    def update_customer_preferences(
        customer_id: int,
        genre: str | None = None,
        author: str | None = None,
        notes: str | None = None,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        """Add a customer reading preference after human approval."""
        return repository.update_customer_preferences(
            customer_id, genre, author, notes, approval_id
        )
