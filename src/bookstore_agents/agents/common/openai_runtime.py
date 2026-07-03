from typing import Any

from bookstore_agents.common.config import get_settings
from bookstore_agents.common.observability import (
    generation_attributes,
    mark_span_error,
    set_span_attributes,
    set_span_output,
    start_span,
)

try:
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore[assignment]


class OpenAITextRuntime:
    def __init__(self) -> None:
        self.settings = get_settings()
        base_url = self._openai_base_url()
        api_key = self.settings.openai_api_key or ("kaos-modelapi" if base_url else None)
        self.client = (
            AsyncOpenAI(api_key=api_key, base_url=base_url)
            if AsyncOpenAI and api_key
            else None
        )

    def _openai_base_url(self) -> str | None:
        base_url = self.settings.openai_base_url or self.settings.model_api_url
        if not base_url:
            return None

        return base_url.rstrip("/")

    async def polish(
        self,
        agent_name: str,
        instructions: str,
        user_message: str,
        context: dict[str, Any],
        fallback: str,
    ) -> str:
        if self.client is None:
            return fallback
        prompt = (
            f"Agent: {agent_name}\n"
            f"Instructions: {instructions}\n"
            f"User message: {user_message}\n"
            f"Structured context: {context}\n\n"
            "Write a concise, useful final answer. Do not invent facts beyond the context."
        )
        if self.client is None:
            return fallback

        attributes = generation_attributes(
            provider="openai",
            model=self.settings.openai_model,
            input_value=prompt,
            agent=agent_name,
            operation="responses",
        )
        with start_span("llm.openai.responses", attributes) as span:
            try:
                response = await self.client.responses.create(
                    model=self.settings.openai_model,
                    input=prompt,
                )
                output = response.output_text or fallback
                set_span_attributes(
                    span,
                    {
                        "gen_ai.response.model": getattr(response, "model", None)
                        or self.settings.openai_model,
                    },
                )
                set_span_output(span, output)
                return output
            except Exception as exc:
                mark_span_error(span, exc)
                set_span_attributes(span, {"bookstore.llm.fallback": True})
                set_span_output(span, fallback)
                return fallback
