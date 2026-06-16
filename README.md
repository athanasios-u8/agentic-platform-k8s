# Local Bookstore Assistant

This repository implements a demo multi-agent bookstore assistant:

- Five independently callable agents
- Three FastMCP servers
- PostgreSQL demo data
- Human approval before write actions
- A2A-style streaming endpoints for agent calls
- ChatKit-oriented frontend gateway and dockerized browser frontend

See the scenario and implementation plan:

- `docs/bookstore-agent-scenario.md`
- `docs/codex-implementation-plan.md`
- `docs/frontend-options.md`

## Quick Start

```bash
cp .env.example .env
uv sync
uv lock
docker compose build
docker compose up -d postgres
docker compose run --rm bookstore-cli .venv/bin/python -m scripts.reset_demo_data
docker compose up
```

If your machine already has Postgres on `5432`, set another host port in `.env`,
for example `POSTGRES_PORT=15432`. The containers still talk to Postgres on
`postgres:5432` internally.

For other host port conflicts, use the `*_HOST_PORT` variables in `.env`. Keep
the non-host `*_PORT` values unchanged unless you also want to change the port
that the service listens on inside its container.

Open the frontend at:

```text
http://localhost:3000
```

The frontend gateway is available at:

```text
http://localhost:8300
```

## Services

| Service | Default host port | Purpose |
|---|---:|---|
| `catalog-mcp` | 8101 | Book search and recommendations |
| `customer-mcp` | 8102 | Customer profiles and preferences |
| `store-operations-mcp` | 8103 | Inventory, reservations, and sales |
| `customer-concierge-agent` | 8201 | Customer-facing master agent |
| `store-manager-agent` | 8202 | Staff-facing master agent |
| `catalog-specialist-agent` | 8203 | Catalog subagent |
| `reservation-specialist-agent` | 8204 | Reservation subagent |
| `message-drafter-agent` | 8205 | No-tool drafting subagent |
| `frontend-gateway` | 8300 | ChatKit gateway and approval routes |
| `frontend` | 3000 | Browser UI |

The host port can be changed with the matching `*_HOST_PORT` variable while the
service keeps its internal container port. For example,
`CATALOG_MCP_HOST_PORT=18101` publishes the Catalog MCP server on host port
`18101` while other containers still reach it at `catalog-mcp:8101`.

## Browser UI

The frontend lets you select any of the five agents and send messages through
the `frontend-gateway`. The active run timeline appears inline below each user
message, so longer conversations scroll inside the conversation pane instead of
creating a second page-level timeline. Changing the selected agent clears the
current chat transcript.

Pending write approvals appear in the sidebar. Approving or rejecting a card
calls the gateway approval route and refreshes the pending approval list.

## Write And Approval Flow

Mutating MCP tools do not write immediately during normal agent runs. The agent
creates a pending approval and returns an `approval_required` event instead.

Approval-gated tools:

- `create_reservation`
- `cancel_reservation`
- `mark_reservation_picked_up`
- `adjust_inventory`
- `update_customer_preferences`

When an approval is accepted, `frontend-gateway` executes the underlying write
tool and stores the `approval_id` with the database update. If the approval is
rejected, no database mutation is performed.

Today's pickup queue only returns active reservations. After a cancellation or
pickup completion is approved, that reservation no longer appears in the
pickup queue.

## Notes

The first implementation provides A2A-compatible HTTP/JSON streaming surfaces and an SDK-ready structure. The agent runtime has deterministic fallbacks so the stack can be exercised without an OpenAI key, but production demo runs should set `OPENAI_API_KEY`.
