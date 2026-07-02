from pathlib import Path

import pytest

from bookstore_agents.agents.catalog_specialist.agent import get_spec as catalog_spec
from bookstore_agents.agents.common.ollama_runtime import OllamaTextRuntime
from bookstore_agents.agents.common.openai_runtime import OpenAITextRuntime
from bookstore_agents.agents.common.runtime import AgentRuntime
from bookstore_agents.agents.release_scout.agent import get_spec as release_scout_spec


def test_release_scout_runtime_uses_ollama_provider() -> None:
    assert isinstance(AgentRuntime(release_scout_spec()).text_runtime, OllamaTextRuntime)
    assert isinstance(AgentRuntime(catalog_spec()).text_runtime, OpenAITextRuntime)


@pytest.mark.asyncio
async def test_release_scout_calls_upcoming_releases_tool_and_polishes_with_runtime():
    runtime = AgentRuntime(release_scout_spec())
    calls = {}

    async def list_tools():
        return {"upcoming_releases": [{"name": "search_upcoming_book_releases"}]}

    async def call_tool(server_name, tool_name, arguments, requires_approval=False):
        calls["server_name"] = server_name
        calls["tool_name"] = tool_name
        calls["arguments"] = arguments
        return {
            "result": {
                "status": "ok",
                "provider": "tavily",
                "query": "upcoming book releases",
                "answer": "",
                "results": [
                    {
                        "title": "The Teashop Spell",
                        "source_url": "https://publisher.example/teashop",
                    }
                ],
            }
        }

    class FakeTextRuntime:
        async def polish(self, agent_name, instructions, user_message, context, fallback):
            calls["polish_context"] = context
            return f"polished: {fallback}"

    runtime.mcp_client.list_tools = list_tools
    runtime._call_tool = call_tool  # type: ignore[method-assign]
    runtime.text_runtime = FakeTextRuntime()

    events = [event async for event in runtime.run("Find upcoming cozy fantasy releases.")]

    assert calls["server_name"] == "upcoming_releases"
    assert calls["tool_name"] == "search_upcoming_book_releases"
    assert calls["arguments"]["theme"] == "cozy fantasy"
    assert "release_search" in calls["polish_context"]
    assert events[-1]["type"] == "final"
    assert events[-1]["answer"].startswith("polished:")


def test_frontend_includes_release_scout_agent_option() -> None:
    html = Path("frontend/index.html").read_text()
    assert 'value="release_scout"' in html
    assert "Release Scout" in html
