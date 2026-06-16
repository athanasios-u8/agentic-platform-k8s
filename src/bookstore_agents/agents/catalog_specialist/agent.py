from bookstore_agents.agents.common.agent_cards import AgentSpec
from bookstore_agents.agents.common.prompts import CATALOG_SPECIALIST_PROMPT
from bookstore_agents.common.config import get_settings


def get_spec() -> AgentSpec:
    settings = get_settings()
    return AgentSpec(
        slug="catalog-specialist",
        name="Catalog Specialist",
        description="Searches and recommends books from the bookstore catalog.",
        role="subagent",
        port=8203,
        mcp_servers={"catalog": settings.catalog_mcp_url},
        instructions=CATALOG_SPECIALIST_PROMPT,
    )
