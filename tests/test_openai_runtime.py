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
