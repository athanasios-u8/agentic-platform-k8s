from bookstore_agents.agents.common.agent_cards import AgentSpec
from bookstore_agents.agents.common.prompts import CUSTOMER_CONCIERGE_PROMPT
from bookstore_agents.common.config import get_settings


def get_spec() -> AgentSpec:
    settings = get_settings()
    return AgentSpec(
        slug="customer-concierge",
        name="Customer Concierge",
        description=(
            "Customer-facing master agent for recommendations, availability, "
            "and reservations."
        ),
        role="master",
        port=8201,
        mcp_servers={
            "catalog": settings.catalog_mcp_url,
            "store_operations": settings.store_operations_mcp_url,
            "customer": settings.customer_mcp_url,
        },
        subagents={
            "catalog_specialist": settings.catalog_specialist_agent_url,
            "reservation_specialist": settings.reservation_specialist_agent_url,
            "message_drafter": settings.message_drafter_agent_url,
            "review_summarizer": settings.review_summarizer_agent_url,
        },
        instructions=CUSTOMER_CONCIERGE_PROMPT,
    )
