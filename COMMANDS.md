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
docker compose logs -f release-scout-agent
docker compose logs -f frontend-gateway
docker compose logs -f frontend
docker compose logs -f otel-collector
```

`release-scout-agent` runs only when the `local-llm` profile is active. The
default Compose stack also starts local trace observability: Collector, Tempo,
and Grafana.

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

Build all backend images plus the browser frontend image:

```bash
make docker-build-all-images
```

Tag images for a registry:

```bash
make docker-build-backend-images BACKEND_IMAGE_PREFIX=ghcr.io/your-org/bookstore IMAGE_TAG=0.1.0
```

## Kubernetes

Use the KAOS deployment for the current full stack, including Release Scout,
Tavily search, and hosted Ollama:

```bash
bash deploy-secret.sh
kubectl kustomize k8s/kaos \
  | yq 'select(.kind != "Secret" or .metadata.name != "bookstore-secrets")' \
  | kubectl apply -f -
kubectl -n bookstore get modelapi,mcpserver,agent
kubectl -n bookstore get pods,svc
kubectl -n bookstore port-forward svc/frontend-gateway 8300:8300
kubectl -n bookstore port-forward svc/frontend 3000:80
```

`deploy-secret.sh` reads `OPENAI_API_KEY` and `TAVILY_API_KEY` from the
environment or `.LOCAL_KEYS`. The filtered apply avoids replacing that real
secret with the placeholders in `k8s/kaos/secrets.yaml`.

For non-local clusters, push the images from `make docker-build-all-images` and
update the image references in each `k8s/kaos/*` component folder.

For plain Kubernetes without KAOS CRDs, use `k8s/base`. It keeps OpenAI
external, and deploys Ollama, the model-pull Job, Upcoming Releases MCP, and
Release Scout as regular Kubernetes resources:

```bash
kubectl apply -k k8s/base
kubectl -n bookstore get deploy,svc,pvc,job
kubectl -n bookstore logs job/ollama-pull-llama3-2-3b
```

## Observability

Observability is enabled by default. Services emit OpenTelemetry traces to the
local Collector. The default Compose stack sends traces to Tempo; the Langfuse
override fans out to both Tempo and local OSS Langfuse.

### Local Startup

```bash
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml --profile local-llm up --build -d
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml --profile cli run --rm bookstore-cli python -m scripts.reset_demo_data
```

This starts the bookstore app, the `local-llm` profile, Tempo, Grafana, the
OpenTelemetry Collector, local Langfuse Web/Worker, Langfuse Postgres,
ClickHouse, Redis, and MinIO. It does not use Langfuse Cloud.

### Local URLs

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
| MinIO console | `http://localhost:9091` |
| Ollama | `http://localhost:11434` |

Langfuse is seeded from `.env` by default:

```text
demo@bookstore.local
bookstore-demo
```

### Health Checks

```bash
curl -fsS http://127.0.0.1:8300/healthz
curl -fsS http://127.0.0.1:8300/agents
curl -fsS http://127.0.0.1:3001/api/health
curl -fsS http://127.0.0.1:3200/ready
curl -fsSI http://127.0.0.1:3002
```

### Smoke Trace

```bash
curl -N --max-time 120 http://127.0.0.1:8300/chat \
  -H 'Content-Type: application/json' \
  -d '{"agent":"catalog_specialist","message":"Recommend one mystery book under $20. Keep the answer brief.","context":{"session_id":"local-observability-smoke"}}'
```

Search Tempo for the named workflow span:

```bash
curl -fsS --get http://127.0.0.1:3200/api/search \
  --data-urlencode 'q={name="frontend.chat"}' \
  --data-urlencode limit=50
```

```bash
curl -fsS 'http://127.0.0.1:3200/api/traces/<trace-id>'
```

In a healthy smoke run, Tempo shows one `POST /chat` trace spanning
`frontend-gateway`, `catalog-specialist-agent`, and `catalog-mcp`. Langfuse
shows the same workflow with prompt, output, tool, and generation observations.

### Logs And Storage Checks

```bash
docker compose logs -f otel-collector
docker compose logs -f tempo
docker compose logs -f grafana
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml logs -f langfuse-web
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml logs -f langfuse-worker
```

```bash
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml --profile local-llm exec -T langfuse-clickhouse sh -lc 'clickhouse-client --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" --query "SELECT count() FROM traces"'
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml --profile local-llm exec -T langfuse-clickhouse sh -lc 'clickhouse-client --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" --query "SELECT count() FROM observations"'
```

### Stop

```bash
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml --profile local-llm down
```

### Kubernetes

Observability runs in the `monitoring` namespace. The bookstore app remains in
`bookstore`, but `bookstore-config` points app traces to
`http://otel-collector.monitoring.svc.cluster.local:4318/v1/traces`.

Use this full order for the KAOS deployment:

```bash
helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm repo update

helm upgrade --install langfuse langfuse/langfuse \
  --namespace monitoring \
  --create-namespace \
  -f k8s/observability/langfuse-values.yaml

kubectl apply -k k8s/kaos-observability

export LANGFUSE_AUTH_STRING="$(grep '^LANGFUSE_AUTH_STRING=' .env | cut -d= -f2-)"

kubectl -n monitoring create secret generic bookstore-observability-secrets \
  --from-literal=LANGFUSE_AUTH_STRING="${LANGFUSE_AUTH_STRING}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n monitoring rollout restart deploy/otel-collector
```

The order matters:

- The Helm command installs self-hosted Langfuse in `monitoring`.
- The overlay applies the bookstore app, Tempo, Grafana, Collector, and the
  cross-namespace OTLP endpoint.
- The overlay also applies `k8s/observability/secrets.yaml`, which is only a
  placeholder with an empty `LANGFUSE_AUTH_STRING`.
- Reapplying the secret after the overlay restores the real Langfuse auth value.
- The Collector reads `LANGFUSE_AUTH_STRING` as an environment variable, so it
  needs a rollout restart after the secret changes.

If `.env` does not already contain `LANGFUSE_AUTH_STRING`, create it from the
Langfuse project public and secret keys:

```bash
LANGFUSE_AUTH_STRING="$(printf 'pk-lf-...:sk-lf-...' | base64 | tr -d '\n')"
```

For plain Kubernetes without KAOS CRDs, replace the overlay command with:

```bash
kubectl apply -k k8s/base-observability
```

If you only want the monitoring stack without applying any app resources, use:

```bash
kubectl apply -k k8s/observability
```

```bash
kubectl -n monitoring port-forward svc/grafana 3001:3000
kubectl -n monitoring port-forward svc/langfuse-web 3002:3000
```

## Local Services Without Docker

```bash
uv run python -m bookstore_agents.mcp_servers.catalog.server
uv run python -m bookstore_agents.mcp_servers.customer.server
uv run python -m bookstore_agents.mcp_servers.store_operations.server
uv run python -m bookstore_agents.mcp_servers.upcoming_releases.server
uv run python -m bookstore_agents.agents.customer_concierge.server
uv run python -m bookstore_agents.agents.store_manager.server
uv run python -m bookstore_agents.agents.catalog_specialist.server
uv run python -m bookstore_agents.agents.reservation_specialist.server
uv run python -m bookstore_agents.agents.message_drafter.server
uv run python -m bookstore_agents.agents.release_scout.server
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

Call Release Scout through the frontend gateway:

```bash
curl -N http://localhost:8300/chat \
  -H 'Content-Type: application/json' \
  -d '{"agent":"release_scout","message":"Find upcoming cozy fantasy releases."}'
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
