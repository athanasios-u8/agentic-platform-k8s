import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from bookstore_agents.common.config import get_settings


class A2AClient:
    def _timeout(self) -> httpx.Timeout:
        settings = get_settings()
        return httpx.Timeout(settings.a2a_stream_timeout_seconds, connect=10.0)

    async def stream_message(
        self, url: str, message: str, context: dict[str, Any] | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            async with client.stream(
                "POST",
                f"{url.rstrip('/')}/a2a/stream",
                json={"message": message, "context": context or {}},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    yield json.loads(line)

    async def final_message(
        self, url: str, message: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        final_event: dict[str, Any] | None = None
        async for event in self.stream_message(url, message, context):
            params = event.get("params", {})
            payload = params.get("event", {})
            if payload.get("type") == "final":
                final_event = payload
        return final_event or {"type": "error", "message": "No final response returned."}
