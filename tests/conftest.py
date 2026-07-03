import pytest

from bookstore_agents.common.config import get_settings


@pytest.fixture(autouse=True)
def disable_external_observability_exports(monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
