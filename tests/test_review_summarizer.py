import pytest

from bookstore_agents.agents.common.openai_runtime import OpenAITextRuntime
from bookstore_agents.agents.common.runtime import AgentRuntime
from bookstore_agents.agents.review_summarizer.agent import get_spec as review_summarizer_spec
from bookstore_agents.azure_ai_search.catalog import BookRecord


def resolved_book() -> BookRecord:
    return BookRecord(
        id=1,
        isbn="978-demo",
        title="The Lantern Cipher",
        title_normalized="the lantern cipher",
        genre="Mystery",
        audience="adult",
        price=18.99,
        description="A twisty mystery.",
        published_year=2024,
        popularity=90,
        authors=["Mara Vale"],
    )


def test_review_summarizer_uses_openai_provider() -> None:
    assert isinstance(AgentRuntime(review_summarizer_spec()).text_runtime, OpenAITextRuntime)


@pytest.mark.asyncio
async def test_review_summarizer_retrieves_reviews_and_polishes() -> None:
    runtime = AgentRuntime(review_summarizer_spec())
    calls = {}

    async def list_tools():
        return {}

    class FakeReviewService:
        def resolve_book(self, message, book_title=None):
            calls["resolved_message"] = message
            return resolved_book()

        def search_for_book(self, book, query, top_k=None):
            calls["search"] = {"book": book.title, "query": query, "top_k": top_k}
            return [
                {
                    "book_title": book.title,
                    "sentiment": "positive",
                    "rating": 5,
                    "headline": "Loved it",
                    "review_text": "Readers liked the puzzle and brisk ending.",
                }
            ]

    class FakeTextRuntime:
        async def polish(self, agent_name, instructions, user_message, context, fallback):
            calls["polish_context"] = context
            return f"polished: {fallback}"

    runtime.mcp_client.list_tools = list_tools
    runtime.review_service = FakeReviewService()
    runtime.text_runtime = FakeTextRuntime()

    events = [event async for event in runtime.run("What do people like about The Lantern Cipher?")]

    assert calls["search"]["top_k"] == 15
    assert calls["polish_context"]["book"]["title"] == "The Lantern Cipher"
    assert events[-1]["type"] == "final"
    assert events[-1]["answer"].startswith("polished:")


@pytest.mark.asyncio
async def test_customer_concierge_delegates_review_questions() -> None:
    from bookstore_agents.agents.customer_concierge.agent import get_spec as concierge_spec

    runtime = AgentRuntime(concierge_spec())
    calls = {}

    async def list_tools():
        return {}

    async def call_subagent(subagent_key, message, context):
        calls["subagent_key"] = subagent_key
        return {
            "type": "subagent_response_received",
            "subagent": subagent_key,
            "answer": "Review summary",
            "data": {},
        }

    runtime.mcp_client.list_tools = list_tools
    runtime._call_subagent = call_subagent  # type: ignore[method-assign]

    events = [event async for event in runtime.run("Summarize reviews for The Lantern Cipher.")]

    assert calls["subagent_key"] == "review_summarizer"
    assert events[-1]["answer"] == "Review summary"
