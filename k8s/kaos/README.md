# KAOS Manifests

This directory deploys the bookstore agents and MCP servers with KAOS custom
resources, without using the KAOS CLI.

It assumes the KAOS operator and CRDs are already installed in the cluster.

## What This Deploys

- `ModelAPI/openai`: LiteLLM proxy to OpenAI using `gpt-5.5`
- `MCPServer/catalog`: existing Catalog FastMCP server as a custom runtime
- `MCPServer/customer`: existing Customer FastMCP server as a custom runtime
- `MCPServer/store-operations`: existing Store Operations FastMCP server as a custom runtime
- Five `Agent` resources that run the existing bookstore agent images
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
- `catalog-mcp/`
- `customer-mcp/`
- `store-operations-mcp/`
- `catalog-specialist-agent/`
- `reservation-specialist-agent/`
- `message-drafter-agent/`
- `customer-concierge-agent/`
- `store-manager-agent/`
- `frontend-gateway/`
- `frontend/`

The custom agent images preserve the current bookstore runtime behavior,
including the human approval flow for mutating tools. The agents receive
`MODEL_API_URL` from the KAOS `ModelAPI` and use it as an OpenAI-compatible
proxy URL.

## Apply

Build and make the images available to your cluster first:

```bash
make docker-build-all-images
```

For a shared cluster, push the images and update the `image:` fields in
the relevant component folders.

Set `bookstore-secrets` with a real `OPENAI_API_KEY` before production use. The
checked-in secret keeps the key empty by design.

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
- `mcpserver-catalog`
- `mcpserver-customer`
- `mcpserver-store-operations`
- `agent-catalog-specialist`
- `agent-reservation-specialist`
- `agent-message-drafter`
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
