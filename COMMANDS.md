# Commands

Run commands from the repository root unless a command says otherwise. The
Makefile wraps the most common local and image-build commands, while the
explicit Docker and Kubernetes commands show the profiles, secrets, and port
forwards used by the demo.

## Local Development

```bash
# Create local config and install/update the Python environment
cp .env.example .env
uv sync
uv lock

# Run quality checks
uv run ruff check .
uv run pytest

# Prepare the demo database in Docker Compose
docker compose up -d postgres
docker compose run --rm bookstore-cli python -m scripts.init_db
docker compose run --rm bookstore-cli python -m scripts.seed_fake_data
docker compose run --rm bookstore-cli python -m scripts.reset_demo_data

# Build and run the lighter runtime stack
make stack-runtime

# Or build and run everything, including observability
make stack-full

# Raise Compose parallelism if your Docker environment has enough headroom
COMPOSE_PARALLEL_LIMIT=2 make stack-full

# Follow full-stack logs
make stack-logs

# Stop either local stack
make stack-down
```

If host port `5432` is already occupied, set `POSTGRES_PORT=15432` in `.env`.
For non-Postgres host port conflicts, set the matching `*_HOST_PORT` value in
`.env` and leave the internal `*_PORT` value unchanged.

```bash
# Same core operations through Make
make sync
make lock
make lint
make test
make stack-runtime
make stack-full
make stack-logs
make stack-down
make reset-db
```

`COMPOSE_PARALLEL_LIMIT` defaults to `1` in the Makefile so image builds and
container starts happen gently on smaller local machines.

## Local Llama 3.2 3B With Ollama

Release Scout is part of the runtime stack. On first run, Compose starts
Ollama, pulls the configured model, starts the Upcoming Releases MCP server,
and then starts `release-scout-agent`.

```bash
# Start the runtime stack
make stack-runtime

# Call Ollama directly after the model is pulled
curl http://localhost:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Hello from the bookstore stack"}],
    "stream": false
  }'

# Follow Release Scout logs
docker compose logs -f release-scout-agent upcoming-releases-mcp ollama

# Stop the runtime stack
make stack-down
```

Configure OpenAI, Ollama, and Tavily independently in `.env`:

```env
OPENAI_MODEL=gpt-5.5
OPENAI_API_KEY=...

OLLAMA_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_API_KEY=ollama
OLLAMA_TIMEOUT_SECONDS=300
A2A_STREAM_TIMEOUT_SECONDS=300

TAVILY_API_KEY=tvly-...
```

Open `http://localhost:3000` and choose `Release Scout` after the runtime stack
is running.

## Images And Kubernetes

```bash
# Build deployable images
make docker-build-agent-mcp-images
make docker-build-backend-images
make docker-build-all-images

# Tag backend images for a registry
make docker-build-backend-images \
  BACKEND_IMAGE_PREFIX=ghcr.io/your-org/bookstore \
  IMAGE_TAG=0.1.0

# Tag every backend and frontend image for a registry
make docker-build-all-images \
  BACKEND_IMAGE_PREFIX=ghcr.io/your-org/bookstore \
  FRONTEND_IMAGE_PREFIX=ghcr.io/your-org/bookstore \
  IMAGE_TAG=0.1.0
```

For KAOS, put `OPENAI_API_KEY` and `TAVILY_API_KEY` in the environment or in
`.LOCAL_KEYS`. The checked-in `k8s/kaos/secrets.yaml` intentionally contains
placeholders.

```bash
# Inspect or apply the real bookstore secret
bash deploy-secret.sh --dry-run
bash deploy-secret.sh

# One-shot KAOS apply from the repo root
bash deploy-resources.sh

# Manual KAOS apply while preserving the real secret
kubectl kustomize k8s/kaos \
  | yq 'select(.kind != "Secret" or .metadata.name != "bookstore-secrets")' \
  | kubectl apply -f -

# Check KAOS resources and browser-facing services
kubectl -n bookstore get modelapi,mcpserver,agent
kubectl -n bookstore get pods,svc
kubectl -n bookstore port-forward svc/frontend-gateway 8300:8300
kubectl -n bookstore port-forward svc/frontend 3000:80

# Restart every Deployment so pods are recreated and pull images as configured
kubectl rollout restart deployment -n bookstore
kubectl rollout status deployment -n bookstore
```

For non-local clusters, push the images from `make docker-build-all-images` and
update the image references in each `k8s/kaos/*` component folder. A rollout
restart recreates Pods, but image re-pulls still follow each container's
`imagePullPolicy`; use `Always` or a new immutable image tag when you need to
guarantee a fresh image.

For plain Kubernetes without KAOS CRDs, use `k8s/base`. It deploys the backend,
MCP servers, agents, gateway, Postgres, Ollama, the model-pull Job, Upcoming
Releases MCP, and Release Scout as regular Kubernetes resources. It does not
include a plain Kubernetes browser frontend manifest.

Review Summarizer is currently local/Compose-only; Kubernetes manifests and
Azure AI Search secrets for that agent are intentionally deferred. The latest
frontend image can show the Review Summarizer option in Kubernetes, but that
option is not backed by a Kubernetes agent service yet.

```bash
# Apply and inspect the plain Kubernetes stack
kubectl apply -k k8s/base
kubectl -n bookstore get deploy,svc,pvc,job
kubectl -n bookstore logs job/ollama-pull-llama3-2-3b
kubectl -n bookstore port-forward svc/frontend-gateway 8300:8300
```

## Observability

Observability is disabled in the lighter runtime stack. `make stack-full` starts
the runtime services plus the OpenTelemetry Collector, Tempo, Grafana, and local
OSS Langfuse; the collector fans out traces to both Tempo and Langfuse.

```bash
# Start the app, Ollama, Tempo, Grafana, Collector, and local Langfuse
make stack-full

# Inspect all runtime and observability containers
docker compose -f docker-compose.yml -f docker-compose.observability.yml ps

# Reset demo data through the Compose CLI profile
docker compose -f docker-compose.yml -f docker-compose.observability.yml \
  --profile cli run --rm bookstore-cli python -m scripts.reset_demo_data

# Health checks
curl -fsS http://127.0.0.1:8300/healthz
curl -fsS http://127.0.0.1:8300/readyz
curl -fsS http://127.0.0.1:8300/agents
curl -fsS http://127.0.0.1:3001/api/health
curl -fsS http://127.0.0.1:3200/ready
curl -fsSI http://127.0.0.1:3002

# Smoke a trace through gateway, agent, and MCP server
curl -N --max-time 120 http://127.0.0.1:8300/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "agent": "catalog_specialist",
    "message": "Recommend one mystery book under $20. Keep the answer brief.",
    "context": {"session_id": "local-observability-smoke"}
  }'

# Search Tempo for the named workflow span and inspect a specific trace
curl -fsS --get http://127.0.0.1:3200/api/search \
  --data-urlencode 'q={name="frontend.chat"}' \
  --data-urlencode limit=50
curl -fsS 'http://127.0.0.1:3200/api/traces/<trace-id>'

# Follow observability logs
docker compose -f docker-compose.yml -f docker-compose.observability.yml logs -f \
  otel-collector tempo grafana langfuse-web langfuse-worker \
  langfuse-clickhouse langfuse-minio langfuse-redis langfuse-postgres

# Check Langfuse ClickHouse storage
docker compose -f docker-compose.yml -f docker-compose.observability.yml \
  exec -T langfuse-clickhouse \
  sh -lc '
    clickhouse-client \
      --user "$CLICKHOUSE_USER" \
      --password "$CLICKHOUSE_PASSWORD" \
      --query "SELECT count() FROM traces"
  '
docker compose -f docker-compose.yml -f docker-compose.observability.yml \
  exec -T langfuse-clickhouse \
  sh -lc '
    clickhouse-client \
      --user "$CLICKHOUSE_USER" \
      --password "$CLICKHOUSE_PASSWORD" \
      --query "SELECT count() FROM observations"
  '

# Stop the local observability stack
make stack-down
```

Local observability URLs:

| Surface | URL |
|---|---|
| Browser frontend | `http://localhost:3000` |
| Frontend gateway health | `http://localhost:8300/healthz` |
| Frontend gateway agents | `http://localhost:8300/agents` |
| Grafana | `http://localhost:3001` |
| Langfuse | `http://localhost:3002` |
| Tempo readiness | `http://localhost:3200/ready` |
| OTel Collector HTTP | `http://localhost:14318/v1/traces` |
| OTel Collector gRPC | `localhost:14317` |
| MinIO API | `http://localhost:9090` |
| MinIO console | `http://localhost:9091` |
| Ollama | `http://localhost:11434` |

Langfuse is seeded from `.env` by default:

```text
demo@bookstore.local
bookstore-demo
```

Observability runs in the Kubernetes `monitoring` namespace. The bookstore app
remains in `bookstore`, but `bookstore-config` points app traces to
`http://otel-collector.monitoring.svc.cluster.local:4318/v1/traces`.

```bash
# Install self-hosted Langfuse and apply the KAOS plus observability overlay
helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm repo update
helm upgrade --install langfuse langfuse/langfuse \
  --namespace monitoring \
  --create-namespace \
  -f k8s/observability/langfuse-values.yaml
kubectl apply -k k8s/kaos-observability

# Restore the real Langfuse auth string after the placeholder secret is applied
export LANGFUSE_AUTH_STRING="$(grep '^LANGFUSE_AUTH_STRING=' .env | cut -d= -f2-)"
kubectl -n monitoring create secret generic bookstore-observability-secrets \
  --from-literal=LANGFUSE_AUTH_STRING="${LANGFUSE_AUTH_STRING}" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n monitoring rollout restart deploy/otel-collector

# Use one of these narrower overlays when you do not want the KAOS app overlay
kubectl apply -k k8s/base-observability
kubectl apply -k k8s/observability

# Port-forward the local Kubernetes UIs
kubectl -n monitoring port-forward svc/grafana 3001:3000
kubectl -n monitoring port-forward svc/langfuse-web 3002:3000
```

The order matters: Helm installs self-hosted Langfuse, the overlay applies the
bookstore app, Tempo, Grafana, Collector, and placeholder observability secret,
and the final secret plus rollout restart restores the real `LANGFUSE_AUTH_STRING`
used by the Collector.

If `.env` does not already contain `LANGFUSE_AUTH_STRING`, create it from the
Langfuse project public and secret keys:

```bash
LANGFUSE_AUTH_STRING="$(printf 'pk-lf-...:sk-lf-...' | base64 | tr -d '\n')"
```

## Local Services Without Docker

These commands run the Python services directly. Start Postgres first and set
`DATABASE_URL`, MCP URLs, agent URLs, and provider keys as needed.

```bash
# MCP servers
uv run python -m bookstore_agents.mcp_servers.catalog.server
uv run python -m bookstore_agents.mcp_servers.customer.server
uv run python -m bookstore_agents.mcp_servers.store_operations.server
uv run python -m bookstore_agents.mcp_servers.upcoming_releases.server

# Agent servers
uv run python -m bookstore_agents.agents.customer_concierge.server
uv run python -m bookstore_agents.agents.store_manager.server
uv run python -m bookstore_agents.agents.catalog_specialist.server
uv run python -m bookstore_agents.agents.reservation_specialist.server
uv run python -m bookstore_agents.agents.message_drafter.server
uv run python -m bookstore_agents.agents.release_scout.server
uv run python -m bookstore_agents.agents.review_summarizer.server

# Frontend gateway
uv run python -m bookstore_agents.frontend_gateway.server
```

## API Smoke Calls

MCP servers expose `/healthz`, `/readyz`, and the FastMCP app mounted at `/mcp`.
Agent servers expose health checks, A2A routes, KAOS-compatible agent cards, and
an OpenAI-compatible chat-completions route. The gateway exposes browser chat,
ChatKit-style streaming, agent discovery, and approvals.

```bash
# Gateway health and discovery
curl -fsS http://localhost:8300/healthz
curl -fsS http://localhost:8300/readyz
curl -fsS http://localhost:8300/agents

# Agent health, cards, A2A JSON-RPC, A2A stream, and chat completions
curl -fsS http://localhost:8201/healthz
curl -fsS http://localhost:8201/.well-known/agent-card.json
curl -fsS http://localhost:8201/.well-known/agent.json
curl -fsS http://localhost:8201/a2a \
  -H 'Content-Type: application/json' \
  -d '{"message":"Find a mystery novel under $20."}'
curl -N http://localhost:8201/a2a/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"Find a mystery novel under $20 and reserve it for customer 1."}'
curl -N http://localhost:8201/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "customer-concierge",
    "messages": [{"role": "user", "content": "Find a mystery novel under $20."}],
    "stream": true
  }'

# Gateway chat, using the same path as the browser UI
curl -N http://localhost:8300/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "agent": "store_manager",
    "message": "Can we cancel the Theo Martin pickup for Signal from Glass Moon?"
  }'

# Release Scout through the gateway; requires the runtime stack or Kubernetes service
curl -N http://localhost:8300/chat \
  -H 'Content-Type: application/json' \
  -d '{"agent":"release_scout","message":"Find upcoming cozy fantasy releases."}'

# Prepare and query Review Summarizer; requires seeded Postgres and Azure AI Search config
docker compose run --rm bookstore-cli bookstore-ai-search rebuild
curl -N http://localhost:8300/chat \
  -H 'Content-Type: application/json' \
  -d '{"agent":"review_summarizer","message":"What do people like and dislike about The Lantern Cipher?"}'

# Approval inspection and resolution
curl -fsS http://localhost:8300/approvals
curl -fsS http://localhost:8300/approvals/<approval_id>
curl -fsS http://localhost:8300/approvals/<approval_id>/approve -X POST
curl -fsS http://localhost:8300/approvals/<approval_id>/reject -X POST
```

After approving a cancellation or pickup completion, ask the Store Manager for
today's pickups again. The pickup list filters to active reservations only.
