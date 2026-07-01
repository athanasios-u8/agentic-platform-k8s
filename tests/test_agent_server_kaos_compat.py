from fastapi.testclient import TestClient

from bookstore_agents.agents.common.server import create_agent_app
from bookstore_agents.agents.message_drafter.agent import get_spec
from bookstore_agents.common.config import get_settings


def test_kaos_agent_card_alias(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    try:
        client = TestClient(create_agent_app(get_spec()))
        response = client.get("/.well-known/agent.json")
        assert response.status_code == 200
        assert response.json()["name"] == "Message Drafter"
    finally:
        get_settings.cache_clear()


def test_kaos_chat_completions_non_streaming(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    try:
        client = TestClient(create_agent_app(get_spec()))
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-5.5",
                "messages": [{"role": "user", "content": "Draft a pickup confirmation."}],
                "stream": False,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["object"] == "chat.completion"
        assert payload["choices"][0]["message"]["content"]
    finally:
        get_settings.cache_clear()
