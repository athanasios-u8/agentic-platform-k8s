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
docker compose run --rm bookstore-cli python -m scripts.init_db
docker compose run --rm bookstore-cli python -m scripts.seed_fake_data
docker compose run --rm bookstore-cli python -m scripts.reset_demo_data
```

If host port `5432` is already occupied, set `POSTGRES_PORT=15432` in `.env`.
For non-Postgres host port conflicts, set the matching `*_HOST_PORT` value in
`.env` and leave the internal `*_PORT` value unchanged.

## Docker

```bash
docker compose build
docker compose up
docker compose logs -f catalog-mcp
docker compose logs -f customer-concierge-agent
docker compose logs -f frontend-gateway
docker compose logs -f frontend
```

## Local Llama 3.2 3B With Ollama

Start the optional CPU-only Ollama service. Its application settings use
`OLLAMA_*` variables and remain separate from `OPENAI_*`.

One command starts Ollama, pulls the configured model, and runs the local stack:

```bash
docker compose --profile local-llm up --build
```

After the model is pulled, you can call Ollama locally:

```bash
curl http://localhost:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Hello from the bookstore stack"}],
    "stream": false
  }'
```

Configure OpenAI and Ollama independently in `.env`:

```env
OPENAI_MODEL=gpt-5.5
OPENAI_API_KEY=...

OLLAMA_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_API_KEY=ollama

TAVILY_API_KEY=tvly-...
```

After updating `.env`, start the stack with the same command:

```bash
docker compose --profile local-llm up --build
```

Open `http://localhost:3000` and choose `Release Scout`.

Build only the deployable agent and MCP images:

```bash
make docker-build-agent-mcp-images
```

Build all backend images, including the generic job image and gateway:

```bash
make docker-build-backend-images
```

Tag images for a registry:

```bash
make docker-build-backend-images BACKEND_IMAGE_PREFIX=ghcr.io/your-org/bookstore IMAGE_TAG=0.1.0
```

## Kubernetes

```bash
kubectl apply -k k8s/base
kubectl -n bookstore get pods
kubectl -n bookstore port-forward svc/frontend-gateway 8300:8300
```

For non-local clusters, push the images from `make docker-build-backend-images`
and update the image references in each service folder's `deployment.yaml` and
in `k8s/base/reset-demo-data/job.yaml`.

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

Call through the frontend gateway, using the same path as the browser UI:

```bash
curl -N http://localhost:8300/chat \
  -H 'Content-Type: application/json' \
  -d '{"agent":"store_manager","message":"Theo Martin called and is not going to pick up Signal from Glass Moon. Can we update the system accordingly?"}'
```

List pending approvals:

```bash
curl http://localhost:8300/approvals
```

Approve a pending write:

```bash
curl http://localhost:8300/approvals/<approval_id>/approve -X POST
```

Reject a pending write:

```bash
curl http://localhost:8300/approvals/<approval_id>/reject -X POST
```

After approving a cancellation or pickup completion, ask the Store Manager for
today's pickups again. The pickup list filters to active reservations only.
