from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from bookstore_agents.agents.common.agent_cards import AgentSpec
from bookstore_agents.agents.common.runtime import AgentRuntime
from bookstore_agents.agents.common.streaming import encode_event, json_rpc_event


class AgentMessageRequest(BaseModel):
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


def create_agent_app(spec: AgentSpec) -> FastAPI:
    runtime = AgentRuntime(spec)
    app = FastAPI(title=spec.name)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": spec.slug}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready", "service": spec.slug}

    @app.get("/.well-known/agent-card.json")
    async def agent_card(request: Request) -> dict[str, Any]:
        return spec.card(str(request.base_url).rstrip("/"))

    @app.post("/a2a")
    async def a2a_message(payload: AgentMessageRequest) -> dict[str, Any]:
        final: dict[str, Any] | None = None
        async for event in runtime.run(payload.message, payload.context):
            if event.get("type") == "final":
                final = event
        return json_rpc_event("final", final or {"answer": "No final response."})

    @app.post("/a2a/stream")
    async def a2a_stream(payload: AgentMessageRequest) -> StreamingResponse:
        async def events():
            async for event in runtime.run(payload.message, payload.context):
                yield encode_event(event.get("type", "event"), event)

        return StreamingResponse(events(), media_type="application/x-ndjson")

    return app


def run_app(app: FastAPI, port: int) -> None:
    uvicorn.run(app, host="0.0.0.0", port=port)
