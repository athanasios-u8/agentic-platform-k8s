from bookstore_agents.common.config import get_settings
from bookstore_agents.mcp_servers.upcoming_releases.repository import (
    UpcomingReleasesRepository,
)


def test_upcoming_releases_returns_missing_api_key(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    get_settings.cache_clear()

    try:
        result = UpcomingReleasesRepository().search_upcoming_book_releases(
            query="cozy fantasy",
            limit=3,
        )
        assert result["status"] == "missing_api_key"
        assert result["provider"] == "tavily"
        assert result["results"] == []
    finally:
        get_settings.cache_clear()


def test_upcoming_releases_normalizes_tavily_results(monkeypatch):
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "query": "upcoming book releases",
                "answer": "Several cozy fantasy releases are listed.",
                "results": [
                    {
                        "title": "Publisher announces The Teashop Spell",
                        "url": "https://publisher.example/books/teashop-spell",
                        "content": "The Teashop Spell will be released on March 12, 2027.",
                        "score": 0.91,
                    }
                ],
            }

    class FakeClient:
        def __init__(self, timeout):
            calls["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def post(self, url, headers, json):
            calls["url"] = url
            calls["headers"] = headers
            calls["json"] = json
            return FakeResponse()

    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setenv("TAVILY_SEARCH_URL", "https://api.tavily.test/search")
    monkeypatch.setattr(
        "bookstore_agents.mcp_servers.upcoming_releases.repository.httpx.Client",
        FakeClient,
    )
    get_settings.cache_clear()

    try:
        result = UpcomingReleasesRepository().search_upcoming_book_releases(
            query="Find cozy fantasy releases",
            theme="cozy fantasy",
            limit=3,
            months_ahead=9,
        )
        assert result["status"] == "ok"
        assert result["answer"] == "Several cozy fantasy releases are listed."
        assert calls["url"] == "https://api.tavily.test/search"
        assert calls["headers"]["Authorization"] == "Bearer tvly-test"
        assert calls["json"]["max_results"] == 3
        assert "cozy fantasy" in calls["json"]["query"]
        first = result["results"][0]
        assert first["source_domain"] == "publisher.example"
        assert first["possible_release_date"] == "March 12, 2027"
    finally:
        get_settings.cache_clear()
