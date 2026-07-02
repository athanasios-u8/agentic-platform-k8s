from bookstore_agents.agents.catalog_specialist.agent import get_spec as catalog_spec
from bookstore_agents.agents.common.runtime import AgentRuntime
from bookstore_agents.agents.customer_concierge.agent import get_spec as concierge_spec
from bookstore_agents.agents.message_drafter.agent import get_spec as drafter_spec
from bookstore_agents.agents.release_scout.agent import get_spec as release_scout_spec
from bookstore_agents.agents.reservation_specialist.agent import get_spec as reservation_spec
from bookstore_agents.agents.store_manager.agent import get_spec as manager_spec
from bookstore_agents.common.config import get_settings


def test_agent_roles_and_independent_ports() -> None:
    specs = [
        concierge_spec(),
        manager_spec(),
        catalog_spec(),
        reservation_spec(),
        drafter_spec(),
        release_scout_spec(),
    ]
    assert {spec.role for spec in specs} == {"master", "subagent"}
    assert [spec.role for spec in specs].count("master") == 2
    assert [spec.role for spec in specs].count("subagent") == 4
    assert len({spec.port for spec in specs}) == 6


def test_message_drafter_has_no_tools() -> None:
    spec = drafter_spec()
    assert spec.mcp_servers == {}
    assert spec.subagents == {}


def test_release_scout_uses_ollama_and_upcoming_releases_mcp(monkeypatch) -> None:
    monkeypatch.setenv("UPCOMING_RELEASES_MCP_URL", "http://localhost:8104/mcp")
    get_settings.cache_clear()

    try:
        spec = release_scout_spec()
        assert spec.model_provider == "ollama"
        assert spec.mcp_servers == {"upcoming_releases": "http://localhost:8104/mcp"}
        assert spec.subagents == {}
    finally:
        get_settings.cache_clear()


def test_master_agents_can_reach_subagents() -> None:
    for spec in [concierge_spec(), manager_spec()]:
        assert "catalog_specialist" in spec.subagents
        assert "reservation_specialist" in spec.subagents
        assert "message_drafter" in spec.subagents


def test_store_manager_detects_pickup_cancellation_request() -> None:
    runtime = AgentRuntime(manager_spec())
    message = (
        'Theo Martin called and is not going to pick up "Signal from Glass Moon". '
        "Can we update the system accordingly?"
    )

    assert runtime._is_cancellation_request(message.lower())
    assert not runtime._is_pickup_completion_request(message.lower())


def test_pickup_match_uses_customer_and_title() -> None:
    runtime = AgentRuntime(manager_spec())
    pickup = {
        "reservation_id": "res-demo-002",
        "customer_name": "Theo Martin",
        "title": "Signal from Glass Moon",
    }
    message = 'Theo Martin is not going to pick up "Signal from Glass Moon".'

    assert runtime._best_pickup_match(message, [pickup]) == pickup
