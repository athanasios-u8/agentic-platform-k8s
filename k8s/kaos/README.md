# KAOS Manifests

This directory deploys the bookstore agents and MCP servers with KAOS custom
resources, without using the KAOS CLI.

It assumes the KAOS operator and CRDs are already installed in the cluster.

## What This Deploys

- `ModelAPI/openai`: LiteLLM proxy to OpenAI using `gpt-5.5`
- `ModelAPI/llama3-2-3b`: hosted Ollama model using `llama3.2:3b`
- `MCPServer/catalog`: existing Catalog FastMCP server as a custom runtime
- `MCPServer/customer`: existing Customer FastMCP server as a custom runtime
- `MCPServer/store-operations`: existing Store Operations FastMCP server as a custom runtime
- `MCPServer/upcoming-releases`: Tavily-backed FastMCP server for upcoming book releases
- Seven `Agent` resources that run the current KAOS-deployed bookstore agent images
  - Existing agents use `ModelAPI/openai`
  - `Agent/release-scout` uses `ModelAPI/llama3-2-3b` and the upcoming releases MCP server
  - `Agent/review-summarizer` uses `ModelAPI/openai` and Azure AI Search review retrieval
- `frontend-gateway`: API gateway for chat and approvals
- `frontend`: browser UI served by nginx
- Postgres, config, secret, and demo-data reset resources needed by the bookstore stack

Review Summarizer is deployed by this KAOS overlay and requires
`AZURE_AI_SEARCH_ENDPOINT` plus either `AZURE_AI_SEARCH_QUERY_KEY` or
`AZURE_AI_SEARCH_ADMIN_KEY` in `bookstore-secrets` to retrieve indexed reviews.

## Layout

Top-level shared resources stay at the root:

- `namespace.yaml`
- `configmap.yaml`
- `secrets.yaml`

Each deployable unit has its own folder and local `kustomization.yaml`:

- `postgres/`
- `reset-demo-data/`
- `openai-modelapi/`
- `llama3-2-3b-modelapi/`
- `catalog-mcp/`
- `customer-mcp/`
- `store-operations-mcp/`
- `upcoming-releases-mcp/`
- `catalog-specialist-agent/`
- `reservation-specialist-agent/`
- `message-drafter-agent/`
- `release-scout-agent/`
- `review-summarizer-agent/`
- `customer-concierge-agent/`
- `store-manager-agent/`
- `frontend-gateway/`
- `frontend/`

The custom agent images preserve the current bookstore runtime behavior,
including the human approval flow for mutating tools. The OpenAI-backed agents
receive `MODEL_API_URL` from `ModelAPI/openai` and use it as an
OpenAI-compatible proxy URL. `release-scout` is intentionally different: it uses
the KAOS-hosted `ModelAPI/llama3-2-3b` service as its Ollama base URL and calls
Ollama's native `/api/chat` endpoint on the generated `modelapi-llama3-2-3b`
service port `11434`.

## Apply

Build and make the images available to your cluster first, then use the helper
script from the repository root:

```bash
# Build all backend, agent, MCP, gateway, and frontend images
make docker-build-all-images

# Apply the KAOS stack in dependency order
bash deploy-resources.sh
```

This rebuilds the browser frontend image too, which is required for the current
agent list, prompt recommendations, and browser-local recent chat history to
appear in the UI. The current frontend includes Review Summarizer in the agent
list, and this KAOS overlay provides the backing agent service.

For a shared cluster, push the images and update the `image:` fields in
the relevant component folders.

Set `bookstore-secrets` with a real `OPENAI_API_KEY` before production use. The
checked-in secret keeps the key empty by design. `MCPServer/upcoming-releases`
also requires `TAVILY_API_KEY`; set it in `bookstore-secrets` before expecting
live internet search results. `Agent/review-summarizer` also requires Azure AI
Search credentials in `bookstore-secrets` before expecting live review
retrieval.

For local deployments, create `.LOCAL_KEYS` in the repository root:

```bash
export DATABASE_URL=...
export POSTGRES_PASSWORD=...
export AZURE_AI_SEARCH_ENDPOINT=...
export OPENAI_API_KEY=...
export TAVILY_API_KEY=...
export AZURE_AI_SEARCH_ADMIN_KEY=...
export AZURE_AI_SEARCH_QUERY_KEY=...
```

`deploy-resources.sh` sources `.LOCAL_KEYS`, calls `deploy-secret.sh`, and then
applies namespace/config resources, Postgres, model APIs, MCP servers, subagents,
master agents, gateway, and frontend resources.

To create or update only the real Kubernetes secret:

```bash
bash deploy-secret.sh
```

Manual apply, preserving the real secret:

```bash
# Shared namespace, config, and real secret
kubectl apply -f k8s/kaos/namespace.yaml
kubectl apply -f k8s/kaos/configmap.yaml
bash deploy-secret.sh

# Data and model APIs
kubectl apply -k k8s/kaos/postgres
kubectl apply -k k8s/kaos/reset-demo-data
kubectl apply -k k8s/kaos/openai-modelapi
kubectl apply -k k8s/kaos/llama3-2-3b-modelapi

# MCP servers
kubectl apply -k k8s/kaos/catalog-mcp
kubectl apply -k k8s/kaos/customer-mcp
kubectl apply -k k8s/kaos/store-operations-mcp
kubectl apply -k k8s/kaos/upcoming-releases-mcp

# Subagents before master/coordinator agents
kubectl apply -k k8s/kaos/catalog-specialist-agent
kubectl apply -k k8s/kaos/reservation-specialist-agent
kubectl apply -k k8s/kaos/message-drafter-agent
kubectl apply -k k8s/kaos/release-scout-agent
kubectl apply -k k8s/kaos/review-summarizer-agent
kubectl apply -k k8s/kaos/customer-concierge-agent
kubectl apply -k k8s/kaos/store-manager-agent

# Browser-facing services
kubectl apply -k k8s/kaos/frontend-gateway
kubectl apply -k k8s/kaos/frontend

# Inspect the result
kubectl -n bookstore get modelapi,mcpserver,agent
kubectl -n bookstore get deploy,svc
```

Do not apply `k8s/kaos/secrets.yaml` over a real cluster secret; it contains
placeholder values by design.

KAOS will create workload services named:

- `modelapi-openai`
- `modelapi-llama3-2-3b`
- `mcpserver-catalog`
- `mcpserver-customer`
- `mcpserver-store-operations`
- `mcpserver-upcoming-releases`
- `agent-catalog-specialist`
- `agent-reservation-specialist`
- `agent-message-drafter`
- `agent-release-scout`
- `agent-review-summarizer`
- `agent-customer-concierge`
- `agent-store-manager`
- `frontend-gateway`
- `frontend`

The KAOS `Agent` and `MCPServer` resources set `podSpec.enableServiceLinks:
false`. This prevents Kubernetes service-link environment variables such as
`FRONTEND_GATEWAY_PORT=tcp://...` from overriding integer application settings
inside the Python containers.

For local browser testing, port-forward both browser-facing services in separate
terminals:

```bash
kubectl -n bookstore port-forward svc/frontend-gateway 8300:8300
kubectl -n bookstore port-forward svc/frontend 3000:80
```

Then open:

```text
http://localhost:3000
```
