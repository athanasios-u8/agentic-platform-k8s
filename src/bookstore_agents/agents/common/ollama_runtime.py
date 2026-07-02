from typing import Any

import httpx

from bookstore_agents.common.config import get_settings


class OllamaTextRuntime:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _chat_url(self) -> str:
        return f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"

    async def polish(
        self,
        agent_name: str,
        instructions: str,
        user_message: str,
        context: dict[str, Any],
        fallback: str,
    ) -> str:
        prompt = (
            f"Agent: {agent_name}\n"
            f"Instructions: {instructions}\n"
            f"User message: {user_message}\n"
            f"Structured context: {context}\n\n"
            "Write a concise, useful final answer. Use only the provided source-backed "
            "context, include source URLs when helpful, and say when the evidence is only "
            "a release lead rather than a confirmed publisher date."
        )
        payload = {
            "model": self.settings.ollama_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(self._chat_url(), json=payload)
                response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content")
            return content or fallback
        except Exception:
            return fallback
