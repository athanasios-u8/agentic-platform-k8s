# Commands

## Local Setup

```bash
cp .env.example .env
uv sync
uv lock
```

## Quality Checks

```bash
uv run ruff check .
uv run pytest
```

## Database

```bash
docker compose up -d postgres
docker compose run --rm bookstore-cli .venv/bin/python -m scripts.init_db
docker compose run --rm bookstore-cli .venv/bin/python -m scripts.seed_fake_data
docker compose run --rm bookstore-cli .venv/bin/python -m scripts.reset_demo_data
```

If host port `5432` is already occupied, set `POSTGRES_PORT=15432` in `.env`.

## Docker

```bash
docker compose build
docker compose up
docker compose logs -f catalog-mcp
docker compose logs -f customer-concierge-agent
docker compose logs -f frontend-gateway
docker compose logs -f frontend
```

## Local Services Without Docker

```bash
uv run python -m bookstore_agents.mcp_servers.catalog.server
uv run python -m bookstore_agents.mcp_servers.customer.server
uv run python -m bookstore_agents.mcp_servers.store_operations.server
uv run python -m bookstore_agents.agents.customer_concierge.server
uv run python -m bookstore_agents.agents.store_manager.server
uv run python -m bookstore_agents.agents.catalog_specialist.server
uv run python -m bookstore_agents.agents.reservation_specialist.server
uv run python -m bookstore_agents.agents.message_drafter.server
uv run python -m bookstore_agents.frontend_gateway.server
```

## Agent Calls

Call an agent directly:

```bash
curl -N http://localhost:8201/a2a/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"Find a mystery novel under $20 and reserve it for customer 1."}'
```

Call the staff-facing master agent:

```bash
curl -N http://localhost:8202/a2a/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"What should I pay attention to before opening today?"}'
```

Approve a pending write:

```bash
curl http://localhost:8300/approvals/<approval_id>/approve -X POST
```

Reject a pending write:

```bash
curl http://localhost:8300/approvals/<approval_id>/reject -X POST
```
