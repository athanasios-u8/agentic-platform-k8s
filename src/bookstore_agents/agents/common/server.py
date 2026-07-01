import json
import time
from typing import Any
from uuid import uuid4

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


def _last_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content", "")
            if isinstance(content, str):
                return content
            return json.dumps(content)
    return ""


def _chat_completion_payload(
    completion_id: str,
    model: str,
    content: str,
    session_id: str,
) -> dict[str, Any]:
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "session_id": session_id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def _chat_completion_chunk(
    completion_id: str,
    model: str,
    content: str,
    session_id: str,
    finish_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "session_id": session_id,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content},
                "finish_reason": finish_reason,
            }
        ],
    }


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

    @app.get("/.well-known/agent.json")
    async def kaos_agent_card(request: Request) -> dict[str, Any]:
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

    @app.post("/v1/chat/completions", response_model=None)
    async def chat_completions(request: Request):
        body = await request.json()
        messages = body.get("messages", [])
        user_message = _last_user_message(messages)
        if not user_message:
            user_message = body.get("message", "")
        model = body.get("model", spec.slug)
        session_id = body.get("session_id") or f"session-{uuid4().hex[:12]}"
        completion_id = f"chatcmpl-{uuid4().hex[:12]}"
        context = {"messages": messages, "session_id": session_id}

        if body.get("stream"):
            async def events():
                step = 0
                async for event in runtime.run(user_message, context):
                    event_type = event.get("type", "event")
                    if event_type == "final":
                        content = str(event.get("answer") or "")
                    else:
                        step += 1
                        content = json.dumps(
                            {
                                "type": "progress",
                                "step": step,
                                "max_steps": 5,
                                "action": event_type,
                                "target": event.get("tool") or event.get("agent") or spec.slug,
                            }
                        )
                    chunk = _chat_completion_chunk(completion_id, model, content, session_id)
                    yield f"data: {json.dumps(chunk)}\n\n"

                chunk = _chat_completion_chunk(completion_id, model, "", session_id, "stop")
                yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                events(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        final: dict[str, Any] | None = None
        async for event in runtime.run(user_message, context):
            if event.get("type") == "final":
                final = event
        answer = str((final or {}).get("answer") or "No final response.")
        return _chat_completion_payload(completion_id, model, answer, session_id)

    return app


def run_app(app: FastAPI, port: int) -> None:
    uvicorn.run(app, host="0.0.0.0", port=port)
