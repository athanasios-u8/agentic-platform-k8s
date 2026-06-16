from bookstore_agents.agents.common.agent_cards import AgentSpec
from bookstore_agents.agents.common.prompts import MESSAGE_DRAFTER_PROMPT


def get_spec() -> AgentSpec:
    return AgentSpec(
        slug="message-drafter",
        name="Message Drafter",
        description="Drafts customer and staff messages from supplied context without tools.",
        role="subagent",
        port=8205,
        instructions=MESSAGE_DRAFTER_PROMPT,
    )
