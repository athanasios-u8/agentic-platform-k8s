from typing import Any

from bookstore_agents.agents.common.runtime import execute_approved_tool
from bookstore_agents.common.approvals import (
    get_approval,
    list_pending_approvals,
    resolve_approval,
)


def pending() -> list[dict[str, Any]]:
    return list_pending_approvals()


def approve(approval_id: str) -> dict[str, Any]:
    approval = resolve_approval(approval_id, approved=True)
    result = execute_approved_tool(approval)
    return {"approval": approval, "result": result}


def reject(approval_id: str) -> dict[str, Any]:
    approval = resolve_approval(approval_id, approved=False)
    return {"approval": approval, "result": None}


def get(approval_id: str) -> dict[str, Any] | None:
    return get_approval(approval_id)
