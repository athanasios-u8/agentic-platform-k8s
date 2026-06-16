from bookstore_agents.agents.common.agent_cards import AgentSpec
from bookstore_agents.agents.common.prompts import RESERVATION_SPECIALIST_PROMPT
from bookstore_agents.common.config import get_settings


def get_spec() -> AgentSpec:
    settings = get_settings()
    return AgentSpec(
        slug="reservation-specialist",
        name="Reservation Specialist",
        description="Checks stock and prepares reservation changes with human approval.",
        role="subagent",
        port=8204,
        mcp_servers={
            "store_operations": settings.store_operations_mcp_url,
            "customer": settings.customer_mcp_url,
        },
        instructions=RESERVATION_SPECIALIST_PROMPT,
    )
