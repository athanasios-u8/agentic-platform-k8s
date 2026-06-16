import json
from typing import Any


def json_rpc_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "method": "message/stream",
        "params": {
            "event": {
                "type": event_type,
                **payload,
            }
        },
    }


def encode_event(event_type: str, payload: dict[str, Any]) -> str:
    return json.dumps(json_rpc_event(event_type, payload), default=str) + "\n"
