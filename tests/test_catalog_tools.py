from bookstore_agents.agents.catalog_specialist.agent import get_spec
from bookstore_agents.agents.common.runtime import AgentRuntime


def test_catalog_runtime_extracts_price_constraint() -> None:
    runtime = AgentRuntime(get_spec())
    assert runtime._extract_max_price("Find a mystery under $20") == 20.0


def test_catalog_runtime_extracts_genre() -> None:
    runtime = AgentRuntime(get_spec())
    assert runtime._extract_genre("Need science fiction") == "Science Fiction"
