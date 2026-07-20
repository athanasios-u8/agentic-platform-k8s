from bookstore_agents.agents.common.agent_cards import AgentSpec
from bookstore_agents.agents.common.prompts import REVIEW_SUMMARIZER_PROMPT


def get_spec() -> AgentSpec:
    return AgentSpec(
        slug="review-summarizer",
        name="Review Summarizer",
        description="Summarizes customer reviews using the configured vector search backend.",
        role="subagent",
        port=8207,
        instructions=REVIEW_SUMMARIZER_PROMPT,
    )
