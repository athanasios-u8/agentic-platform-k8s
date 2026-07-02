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
