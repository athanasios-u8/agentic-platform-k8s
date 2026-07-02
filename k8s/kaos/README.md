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
- Six `Agent` resources that run the bookstore agent images
  - Existing agents use `ModelAPI/openai`
  - `Agent/release-scout` uses `ModelAPI/llama3-2-3b` and the upcoming releases MCP server
- `frontend-gateway`: API gateway for chat and approvals
- `frontend`: browser UI served by nginx
- Postgres, config, secret, and demo-data reset resources needed by the bookstore stack

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

Build and make the images available to your cluster first:

```bash
make docker-build-all-images
```

This rebuilds the browser frontend image too, which is required for the
`Release Scout` selector option and starter prompt to appear in the UI.

For a shared cluster, push the images and update the `image:` fields in
the relevant component folders.

Set `bookstore-secrets` with a real `OPENAI_API_KEY` before production use. The
checked-in secret keeps the key empty by design. `MCPServer/upcoming-releases`
also requires `TAVILY_API_KEY`; set it in `bookstore-secrets` before expecting
live internet search results.

```bash
kubectl apply -k k8s/kaos
```

Useful checks:

```bash
kubectl -n bookstore get modelapi,mcpserver,agent
kubectl -n bookstore get deploy,svc
```

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
- `agent-customer-concierge`
- `agent-store-manager`
- `frontend-gateway`
- `frontend`

For local browser testing, port-forward both browser-facing services:

```bash
kubectl -n bookstore port-forward svc/frontend-gateway 8300:8300
kubectl -n bookstore port-forward svc/frontend 3000:80
```

Then open:

```text
http://localhost:3000
```
