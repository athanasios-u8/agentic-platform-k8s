import re
from typing import Any
from urllib.parse import urlparse

import httpx

from bookstore_agents.common.config import get_settings


class UpcomingReleasesRepository:
    def __init__(self) -> None:
        self.settings = get_settings()

    def search_upcoming_book_releases(
        self,
        query: str,
        author: str | None = None,
        theme: str | None = None,
        limit: int = 5,
        months_ahead: int = 12,
    ) -> dict[str, Any]:
        search_query = self._build_query(query, author, theme, months_ahead)
        if not self.settings.tavily_api_key:
            return {
                "status": "missing_api_key",
                "provider": "tavily",
                "query": search_query,
                "answer": "",
                "results": [],
                "message": "Set TAVILY_API_KEY to enable upcoming release web search.",
            }

        payload = {
            "query": search_query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": max(1, min(int(limit), 20)),
            "include_answer": "basic",
            "include_raw_content": False,
            "include_images": False,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.tavily_api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    self.settings.tavily_search_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return {
                "status": "search_error",
                "provider": "tavily",
                "query": search_query,
                "answer": "",
                "results": [],
                "error": str(exc),
            }

        return {
            "status": "ok",
            "provider": "tavily",
            "query": data.get("query") or search_query,
            "answer": data.get("answer") or "",
            "results": [self._normalize_result(result) for result in data.get("results", [])],
        }

    def _build_query(
        self,
        query: str,
        author: str | None,
        theme: str | None,
        months_ahead: int,
    ) -> str:
        parts = ["upcoming book releases", f"next {int(months_ahead)} months"]
        if author:
            parts.append(f"author {author}")
        if theme:
            parts.append(f"theme or genre {theme}")
        if query:
            parts.append(query)
        parts.append("publisher release date preorder ISBN")
        return " ".join(parts)

    def _normalize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        url = str(result.get("url") or "")
        snippet = str(result.get("content") or "")
        return {
            "title": result.get("title") or "Untitled source",
            "source_url": url,
            "source_domain": result.get("domain") or urlparse(url).netloc,
            "snippet": snippet,
            "published_date": result.get("published_date"),
            "possible_release_date": self._extract_release_date(snippet),
            "score": result.get("score"),
        }

    def _extract_release_date(self, text: str) -> str | None:
        iso_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
        if iso_match:
            return iso_match.group(0)
        month_names = (
            "Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            "Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
            "Dec(?:ember)?"
        )
        month_match = re.search(
            rf"\b(?:{month_names})\s+\d{{1,2}},?\s+\d{{4}}\b",
            text,
            re.IGNORECASE,
        )
        return month_match.group(0) if month_match else None
