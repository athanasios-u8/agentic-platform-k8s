import json
from typing import Any


def extract_chatkit_message(body: bytes) -> tuple[str, dict[str, Any]]:
    if not body:
        return "", {}
    payload = json.loads(body)
    context = payload.get("context") or payload.get("metadata") or {}

    if isinstance(payload.get("message"), str):
        return payload["message"], context

    input_item = payload.get("input")
    if isinstance(input_item, dict):
        content = input_item.get("content")
        if isinstance(content, str):
            return content, context
        if isinstance(content, list):
            text_parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") in {"text", "input_text"}
            ]
            if text_parts:
                return "\n".join(text_parts), context

    messages = payload.get("messages") or []
    if messages:
        last = messages[-1]
        if isinstance(last, dict):
            content = last.get("content", "")
            if isinstance(content, str):
                return content, context
            if isinstance(content, list):
                return "\n".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("text")
                ), context

    return json.dumps(payload), context


def extract_agent_key(headers: dict[str, str], context: dict[str, Any]) -> str:
    return (
        context.get("agent")
        or context.get("agent_key")
        or headers.get("x-agent-key")
        or headers.get("X-Agent-Key")
        or "customer_concierge"
    )
