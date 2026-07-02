from bookstore_agents.agents.common.runtime import AgentRuntime
from bookstore_agents.agents.release_scout.agent import get_spec


def get_runtime() -> AgentRuntime:
    return AgentRuntime(get_spec())
