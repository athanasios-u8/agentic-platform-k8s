from bookstore_agents.agents.common.agent_cards import AgentSpec
from bookstore_agents.agents.common.prompts import STORE_MANAGER_PROMPT
from bookstore_agents.common.config import get_settings


def get_spec() -> AgentSpec:
    settings = get_settings()
    return AgentSpec(
        slug="store-manager",
        name="Store Manager",
        description="Staff-facing master agent for daily operations, sales, stock, and pickups.",
        role="master",
        port=8202,
        mcp_servers={
            "catalog": settings.catalog_mcp_url,
            "store_operations": settings.store_operations_mcp_url,
        },
        subagents={
            "catalog_specialist": settings.catalog_specialist_agent_url,
            "reservation_specialist": settings.reservation_specialist_agent_url,
            "message_drafter": settings.message_drafter_agent_url,
        },
        instructions=STORE_MANAGER_PROMPT,
    )
