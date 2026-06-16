import json
from typing import Any
from uuid import uuid4

from bookstore_agents.common.database import connection, fetch_all, fetch_one

WRITE_TOOLS = {
    "create_reservation",
    "cancel_reservation",
    "mark_reservation_picked_up",
    "adjust_inventory",
    "update_customer_preferences",
}


def create_approval(
    agent_name: str,
    tool_name: str,
    arguments: dict[str, Any],
    summary: str,
    run_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    approval_id = f"appr-{uuid4().hex[:12]}"
    with connection() as conn:
        with conn.cursor() as cur:
            row = cur.execute(
                """
                INSERT INTO approvals (
                    approval_id, agent_name, tool_name, arguments, summary, status, run_state
                )
                VALUES (%s, %s, %s, %s::jsonb, %s, 'pending', %s::jsonb)
                RETURNING approval_id, agent_name, tool_name, arguments, summary, status, run_state,
                          created_at, updated_at
                """,
                (
                    approval_id,
                    agent_name,
                    tool_name,
                    json.dumps(arguments),
                    summary,
                    json.dumps(run_state or {}),
                ),
            ).fetchone()
            return dict(row)


def list_pending_approvals() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT approval_id, agent_name, tool_name, arguments, summary, status, run_state,
               created_at, updated_at
        FROM approvals
        WHERE status = 'pending'
        ORDER BY created_at ASC
        """
    )


def get_approval(approval_id: str) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT approval_id, agent_name, tool_name, arguments, summary, status, run_state,
               created_at, updated_at
        FROM approvals
        WHERE approval_id = %s
        """,
        (approval_id,),
    )


def resolve_approval(approval_id: str, approved: bool) -> dict[str, Any]:
    status = "approved" if approved else "rejected"
    with connection() as conn:
        with conn.cursor() as cur:
            row = cur.execute(
                """
                UPDATE approvals
                SET status = %s, updated_at = NOW()
                WHERE approval_id = %s
                RETURNING approval_id, agent_name, tool_name, arguments, summary, status, run_state,
                          created_at, updated_at
                """,
                (status, approval_id),
            ).fetchone()
            if not row:
                raise ValueError(f"Approval {approval_id} was not found.")
            return dict(row)
