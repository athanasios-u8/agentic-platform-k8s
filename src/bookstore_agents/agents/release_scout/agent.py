from bookstore_agents.agents.common.agent_cards import AgentSpec
from bookstore_agents.agents.common.prompts import RELEASE_SCOUT_PROMPT
from bookstore_agents.common.config import get_settings


def get_spec() -> AgentSpec:
    settings = get_settings()
    return AgentSpec(
        slug="release-scout",
        name="Release Scout",
        description="Finds upcoming book releases by author, theme, or genre.",
        role="subagent",
        port=8206,
        mcp_servers={"upcoming_releases": settings.upcoming_releases_mcp_url},
        instructions=RELEASE_SCOUT_PROMPT,
        model_provider="ollama",
    )
