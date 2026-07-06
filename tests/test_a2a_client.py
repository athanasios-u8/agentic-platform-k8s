from bookstore_agents.agents.common.a2a_client import A2AClient
from bookstore_agents.common.config import get_settings


def test_a2a_client_uses_configured_stream_timeout(monkeypatch) -> None:
    monkeypatch.setenv("A2A_STREAM_TIMEOUT_SECONDS", "234")
    get_settings.cache_clear()

    try:
        timeout = A2AClient()._timeout()
        assert timeout.connect == 10.0
        assert timeout.read == 234.0
    finally:
        get_settings.cache_clear()
