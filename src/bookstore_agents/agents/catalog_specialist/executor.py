from bookstore_agents.agents.catalog_specialist.agent import get_spec
from bookstore_agents.agents.common.runtime import AgentRuntime


def get_runtime() -> AgentRuntime:
    return AgentRuntime(get_spec())
