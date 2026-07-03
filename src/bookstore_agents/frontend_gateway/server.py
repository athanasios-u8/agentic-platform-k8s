import json
from collections.abc import AsyncIterator
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from bookstore_agents.agents.common.a2a_client import A2AClient
from bookstore_agents.common.config import get_port, get_settings
from bookstore_agents.common.observability import (
    instrument_fastapi_app,
    set_span_output,
    start_span,
    workflow_attributes,
)
from bookstore_agents.frontend_gateway import approvals
from bookstore_agents.frontend_gateway.chatkit_server import (
    extract_agent_key,
    extract_chatkit_message,
)
from bookstore_agents.frontend_gateway.streaming import extract_agent_event, ndjson_to_sse


class ChatRequest(BaseModel):
    agent: str = "customer_concierge"
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


def agent_urls() -> dict[str, str]:
    settings = get_settings()
    return {
        "customer_concierge": settings.customer_concierge_agent_url,
        "store_manager": settings.store_manager_agent_url,
        "catalog_specialist": settings.catalog_specialist_agent_url,
        "reservation_specialist": settings.reservation_specialist_agent_url,
        "message_drafter": settings.message_drafter_agent_url,
        "release_scout": settings.release_scout_agent_url,
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Bookstore Frontend Gateway")
    instrument_fastapi_app(app, "frontend-gateway")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    client = A2AClient()

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "frontend-gateway"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready", "service": "frontend-gateway"}

    @app.get("/agents")
    async def agents() -> dict[str, str]:
        return agent_urls()

    @app.post("/chat")
    async def chat(payload: ChatRequest) -> StreamingResponse:
        urls = agent_urls()
        if payload.agent not in urls:
            raise HTTPException(status_code=404, detail=f"Unknown agent {payload.agent}.")

        async def stream() -> AsyncIterator[str]:
            attributes = workflow_attributes(
                agent=payload.agent,
                event="frontend.chat",
                input_value=payload.message,
                session_id=payload.context.get("session_id"),
                extra={"bookstore.gateway.route": "/chat"},
            )
            with start_span("frontend.chat", attributes) as span:
                async for event in client.stream_message(
                    urls[payload.agent], payload.message, payload.context
                ):
                    params = event.get("params", {}) if isinstance(event, dict) else {}
                    payload_event = params.get("event", {}) if isinstance(params, dict) else {}
                    if payload_event.get("type") == "final":
                        set_span_output(
                            span,
                            payload_event.get("answer") or payload_event,
                            trace_output=True,
                        )
                    yield json.dumps(event, default=str) + "\n"

        return StreamingResponse(stream(), media_type="application/x-ndjson")

    @app.post("/chatkit")
    async def chatkit(request: Request) -> Response:
        body = await request.body()
        message, context = extract_chatkit_message(body)
        agent_key = extract_agent_key(dict(request.headers), context)
        urls = agent_urls()
        if agent_key not in urls:
            agent_key = "customer_concierge"

        async def events() -> AsyncIterator[dict[str, Any]]:
            attributes = workflow_attributes(
                agent=agent_key,
                event="frontend.chatkit",
                input_value=message,
                session_id=context.get("session_id"),
                extra={"bookstore.gateway.route": "/chatkit"},
            )
            with start_span("frontend.chatkit", attributes) as span:
                async for event in client.stream_message(urls[agent_key], message, context):
                    extracted = extract_agent_event(event)
                    if extracted.get("type") == "final":
                        set_span_output(
                            span,
                            extracted.get("answer") or extracted,
                            trace_output=True,
                        )
                    yield extracted

        return StreamingResponse(ndjson_to_sse(events()), media_type="text/event-stream")

    @app.get("/approvals")
    async def list_approvals() -> list[dict[str, Any]]:
        return approvals.pending()

    @app.get("/approvals/{approval_id}")
    async def get_approval(approval_id: str) -> dict[str, Any]:
        approval = approvals.get(approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found.")
        return approval

    @app.post("/approvals/{approval_id}/approve")
    async def approve(approval_id: str) -> dict[str, Any]:
        return approvals.approve(approval_id)

    @app.post("/approvals/{approval_id}/reject")
    async def reject(approval_id: str) -> dict[str, Any]:
        return approvals.reject(approval_id)

    return app


app = create_app()


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=get_port("FRONTEND_GATEWAY_PORT", 8300))


if __name__ == "__main__":
    main()
