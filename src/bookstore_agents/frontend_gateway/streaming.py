import json
from collections.abc import AsyncIterator
from typing import Any


async def ndjson_to_sse(events: AsyncIterator[dict[str, Any]]) -> AsyncIterator[str]:
    async for event in events:
        yield f"data: {json.dumps(event, default=str)}\n\n"


def extract_agent_event(json_rpc_event: dict[str, Any]) -> dict[str, Any]:
    return json_rpc_event.get("params", {}).get("event", json_rpc_event)
