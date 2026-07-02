import pytest

from bookstore_agents.agents.common.ollama_runtime import OllamaTextRuntime
from bookstore_agents.agents.common.openai_runtime import OpenAITextRuntime
from bookstore_agents.common.config import get_settings


def test_model_api_url_is_used_as_openai_base_url(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("MODEL_API_URL", "http://modelapi-openai.bookstore.svc.cluster.local:8000/")
    get_settings.cache_clear()

    try:
        runtime = OpenAITextRuntime()
        assert runtime._openai_base_url() == (
            "http://modelapi-openai.bookstore.svc.cluster.local:8000"
        )
    finally:
        get_settings.cache_clear()


def test_openai_base_url_overrides_model_api_url(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://litellm.example:4000")
    monkeypatch.setenv("MODEL_API_URL", "http://modelapi-openai:8000")
    get_settings.cache_clear()

    try:
        runtime = OpenAITextRuntime()
        assert runtime._openai_base_url() == "http://litellm.example:4000"
    finally:
        get_settings.cache_clear()


def test_openai_and_ollama_settings_are_independent(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.5")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_API_KEY", "ollama")
    get_settings.cache_clear()

    try:
        settings = get_settings()
        assert settings.openai_model == "gpt-5.5"
        assert settings.openai_api_key == "openai-key"
        assert settings.ollama_model == "llama3.2:3b"
        assert settings.ollama_base_url == "http://ollama:11434"
        assert settings.ollama_api_key == "ollama"
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_ollama_runtime_posts_to_native_chat_api(monkeypatch):
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "Ollama polished answer"}}

    class FakeAsyncClient:
        def __init__(self, timeout):
            calls["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            calls["url"] = url
            calls["json"] = json
            return FakeResponse()

    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434/")
    monkeypatch.setattr(
        "bookstore_agents.agents.common.ollama_runtime.httpx.AsyncClient",
        FakeAsyncClient,
    )
    get_settings.cache_clear()

    try:
        runtime = OllamaTextRuntime()
        result = await runtime.polish("Release Scout", "Instructions", "Prompt", {}, "fallback")
        assert result == "Ollama polished answer"
        assert calls["url"] == "http://ollama:11434/api/chat"
        assert calls["json"]["model"] == "llama3.2:3b"
        assert calls["json"]["stream"] is False
        assert calls["json"]["messages"][0]["role"] == "user"
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_ollama_runtime_returns_fallback_on_error(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            raise RuntimeError("ollama unavailable")

    monkeypatch.setattr(
        "bookstore_agents.agents.common.ollama_runtime.httpx.AsyncClient",
        FakeAsyncClient,
    )
    get_settings.cache_clear()

    try:
        runtime = OllamaTextRuntime()
        result = await runtime.polish("Release Scout", "Instructions", "Prompt", {}, "fallback")
        assert result == "fallback"
    finally:
        get_settings.cache_clear()
