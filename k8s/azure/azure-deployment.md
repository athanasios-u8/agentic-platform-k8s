# Azure dev deployment command log

This runbook records the commands used to build, deploy, populate, and verify
the dev Azure AKS environment for the bookstore agent platform.

It intentionally omits secret values. Commands that execute inline Python read
configuration from the running pods and do not print connection strings,
passwords, tokens, or API keys.

## Environment

- Azure resource group: `nucleus_swec_dev-rg`
- AKS cluster: `aks-nucleus-dev-swec-001`
- Namespace: `nucleus`
- Monitoring namespace: `monitoring`
- ACR: `acrnucleusdevswec001.azurecr.io`
- PostgreSQL server: `psql-nucleus-dev-swec-001.postgres.database.azure.com`
- Azure AI Search service: `srch-nucleus-dev-swec-001`
- Azure AI Search index: `srch-index-bookstore-dev`
- Azure Foundry endpoint: `https://aif-nucleus-dev-swec-001.openai.azure.com`
- Azure Foundry deployment: `model-nucleus-dev-swec-001`

## Azure and AKS context

```bash
az account show
```

```bash
az resource list \
  --resource-group nucleus_swec_dev-rg \
  --output table
```

```bash
az aks get-credentials \
  --resource-group nucleus_swec_dev-rg \
  --name aks-nucleus-dev-swec-001 \
  --overwrite-existing
```

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl get nodes
```

## KAOS operator

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl get crd | grep kaos
```

```bash
helm upgrade --install kaos-operator ../kaos/operator/chart \
  -n kaos-system \
  --create-namespace \
  --set defaultImages.litellm=acrnucleusdevswec001.azurecr.io/bookstore/litellm:main-stable \
  --set defaultImages.ollama=acrnucleusdevswec001.azurecr.io/bookstore/ollama:latest \
  --wait \
  --timeout 5m
```

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl get pods -n kaos-system
```

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl get crd | grep kaos
```

## Build and push images

Each Python service image is built with its own default
`BOOKSTORE_SERVICE_MODULE`. The Azure manifests also set that variable
explicitly, so the image is self-describing and the deployed configuration is
visible in Kubernetes. The Dockerfile keeps the service-specific layer after
the dependency layers so independent builds reuse the same cache.

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 make docker-build-backend-images \
  BACKEND_IMAGE_PREFIX=acrnucleusdevswec001.azurecr.io/bookstore \
  IMAGE_TAG=dev
```

```bash
ACR="acrnucleusdevswec001.azurecr.io"

for service in \
  backend \
  catalog-mcp \
  customer-mcp \
  store-operations-mcp \
  upcoming-releases-mcp \
  catalog-specialist-agent \
  reservation-specialist-agent \
  message-drafter-agent \
  release-scout-agent \
  review-summarizer-agent \
  customer-concierge-agent \
  store-manager-agent \
  frontend-gateway
do
  docker push "$ACR/bookstore/$service:dev"
done
```

```bash
ACR="acrnucleusdevswec001.azurecr.io"

docker buildx build \
  --platform linux/amd64 \
  -t "$ACR/bookstore/frontend:dev" \
  --push frontend
```

Mirror runtime images that the cluster needs before enabling VNet-restricted
deployment:

```bash
k8s/azure/scripts/mirror-runtime-images.sh
```

The final backend and frontend-gateway image digest rolled out during this dev
deployment was:

```text
sha256:c679627d0be545ecaab82a19ba07f88c9aeba9fdea9e42c725df640704707348
```

## Deploy observability and application manifests

Azure observability has its own complete deployment package. Deploy it before
the application because the Azure application ConfigMap enables tracing by
default:

```bash
k8s/azure/observability/dev/deploy.sh
```

This installs pinned Langfuse chart `1.5.39` with the managed Azure PostgreSQL
`langfuse` database and applies the Azure-owned Tempo, Grafana, and Collector
manifests. It does not read the local `k8s/observability` directory.

## Optional secure VNet mode

Create the existing VNet input before setting `deployment_in_vnet = true`:

```bash
az network vnet create \
  --resource-group nucleus_swec_dev-rg \
  --location swedencentral \
  --name vnet-nucleus-dev-swec-001 \
  --address-prefixes 10.80.0.0/16
```

Confirm it exists:

```bash
az network vnet show \
  --resource-group nucleus_swec_dev-rg \
  --name vnet-nucleus-dev-swec-001 \
  --query "{name:name,addressSpace:addressSpace.addressPrefixes,location:location}"
```

Public mode preview:

```bash
terraform -chdir=infra/azure/terraform plan \
  -var-file=environments/dev/terraform.tfvars \
  -var='deployment_in_vnet=false'
```

Secure VNet mode, using the checked-in dev tfvars:

```bash
terraform -chdir=infra/azure/terraform plan \
  -var-file=environments/dev/terraform.tfvars
```

In VNet mode, AKS and PostgreSQL are rebuilt and the PostgreSQL and AI Search
population jobs must be rerun. The frontend remains private; use port-forward
for now. A future NGINX ingress can reserve a Terraform-managed public IP when
`enable_future_nginx_ingress_ip` is enabled and should use
`loadBalancerSourceRanges: ["20.250.178.236/32"]`.

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl apply -k k8s/azure/dev
```

After manifest corrections, the bundle was validated with a server-side dry
run before applying again:

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl apply -k k8s/azure/dev --dry-run=server
```

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl apply -k k8s/azure/dev
```

## Populate Azure PostgreSQL

```bash
k8s/azure/scripts/populate-postgres.sh \
  --environment dev \
  --yes
```

The population Job runs:

```bash
python -m scripts.reset_demo_data
```

That module calls:

```bash
python -m scripts.init_db
python -m scripts.seed_fake_data
```

## Populate Azure AI Search

```bash
k8s/azure/scripts/populate-ai-search.sh \
  --environment dev \
  --yes
```

The dev Search population Job creates or updates the Search index and uploads
the checked-in synthetic review seed data from
`data/book_reviews/book_reviews.jsonl` with the `nucleus-indexer` workload
identity. This uploaded 489 review documents during the private VNet deployment.

## Azure AI Search managed identity auth fix

The Search service initially rejected managed identity calls because it was in
API-key-only mode. This command enabled both Microsoft Entra and API-key auth:

```bash
az search service update \
  --resource-group nucleus_swec_dev-rg \
  --name srch-nucleus-dev-swec-001 \
  --auth-options aadOrApiKey \
  --aad-auth-failure-mode http401WithBearerChallenge
```

The Terraform configuration was updated to preserve that setting.

## Roll out refreshed images

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout restart \
  deployment/agent-catalog-specialist \
  deployment/agent-customer-concierge \
  deployment/agent-message-drafter \
  deployment/agent-release-scout \
  deployment/agent-reservation-specialist \
  deployment/agent-review-summarizer \
  deployment/agent-store-manager \
  deployment/mcpserver-catalog \
  deployment/mcpserver-customer \
  deployment/mcpserver-store-operations \
  deployment/mcpserver-upcoming-releases \
  deployment/frontend-gateway
```

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/agent-catalog-specialist --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/agent-customer-concierge --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/agent-message-drafter --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/agent-release-scout --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/agent-reservation-specialist --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/agent-review-summarizer --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/agent-store-manager --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/mcpserver-catalog --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/mcpserver-customer --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/mcpserver-store-operations --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/mcpserver-upcoming-releases --timeout=180s
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus rollout status deployment/frontend-gateway --timeout=180s
```

## Live verification

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus get deploy,po,svc,job
```

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus get modelapi,mcpserver,agent
```

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus get pods \
  -o custom-columns='NAME:.metadata.name,READY:.status.containerStatuses[*].ready,IMAGE:.spec.containers[*].image,IMAGE_ID:.status.containerStatuses[*].imageID'
```

### PostgreSQL counts

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus exec -i deploy/frontend-gateway -- python - <<'PY'
from bookstore_agents.common.database import fetch_value

for table in [
    "authors",
    "books",
    "book_authors",
    "inventory",
    "customers",
    "customer_preferences",
    "reservations",
    "sales",
    "approvals",
]:
    print(f"{table}: {fetch_value(f'SELECT COUNT(*) FROM {table}')}")
PY
```

Expected dev result after the recorded run:

```text
authors: 21
books: 40
book_authors: 40
inventory: 40
customers: 12
customer_preferences: 12
reservations: 5
sales: 86
approvals: 0
```

### Azure AI Search counts and sample query

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus exec -i deploy/agent-review-summarizer -- python - <<'PY'
from bookstore_agents.vector_search.factory import create_vector_search_backend

backend = create_vector_search_backend()
print(f"search_documents: {backend.count_documents()}")

rows = backend.search_reviews(
    "the lantern cipher",
    "What do readers like and dislike?",
    top=3,
)

print(f"lantern_cipher_hits: {len(rows)}")
for row in rows:
    print(f"- {row['sentiment']} / {row['rating']} / {row['headline']}")
PY
```

Expected dev result after the recorded run:

```text
search_documents: 489
lantern_cipher_hits: 3
```

### Gateway and agent smoke test

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus exec -i deploy/frontend-gateway -- python - <<'PY'
import json
import urllib.request

for name, url in [
    ("gateway_health", "http://frontend-gateway:8300/healthz"),
    ("gateway_ready", "http://frontend-gateway:8300/readyz"),
    ("gateway_agents", "http://frontend-gateway:8300/agents"),
    ("catalog_agent_health", "http://agent-catalog-specialist:8000/healthz"),
    ("catalog_mcp_health", "http://mcpserver-catalog:8000/healthz"),
    ("openai_modelapi_health", "http://modelapi-openai:8000/health/liveliness"),
]:
    with urllib.request.urlopen(url, timeout=15) as response:
        print(f"{name}: {response.status}")

payload = json.dumps({
    "agent": "review_summarizer",
    "message": "Summarize reader sentiment for The Lantern Cipher in one sentence.",
    "context": {"session_id": "azure-final-smoke"},
}).encode()

request = urllib.request.Request(
    "http://frontend-gateway:8300/chat",
    data=payload,
    headers={"Content-Type": "application/json"},
)

with urllib.request.urlopen(request, timeout=120) as response:
    final_answer = None
    for raw in response:
        event = json.loads(raw)
        payload_event = event.get("params", {}).get("event", {})
        if payload_event.get("type") == "final":
            final_answer = payload_event.get("answer")
    print(f"chat_review_summarizer: {response.status}; final={final_answer}")
PY
```

Expected health result:

```text
gateway_health: 200
gateway_ready: 200
gateway_agents: 200
catalog_agent_health: 200
catalog_mcp_health: 200
openai_modelapi_health: 200
chat_review_summarizer: 200
```

## Local validation

```bash
python3 "$HOME/.codex/skills/align-env-files/scripts/check_env_alignment.py" --no-order
```

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl kustomize k8s/azure/dev > /tmp/nucleus-azure-dev.yaml
PATH=/private/tmp/aks-tools:$PATH kubectl kustomize k8s/azure/observability/dev > /tmp/nucleus-azure-observability-dev.yaml
helm template langfuse langfuse/langfuse \
  --version 1.5.39 \
  --namespace monitoring \
  -f k8s/azure/observability/dev/langfuse-values.yaml \
  > /tmp/nucleus-azure-langfuse-dev.yaml
PATH=/private/tmp/aks-tools:$PATH kubectl kustomize k8s/azure/database/dev > /tmp/nucleus-azure-db-dev.yaml
PATH=/private/tmp/aks-tools:$PATH kubectl kustomize k8s/azure/search/dev > /tmp/nucleus-azure-search-dev.yaml
```

```bash
terraform -chdir=infra/azure/terraform fmt -check
terraform -chdir=infra/azure/terraform validate
```

```bash
uv lock
uv run ruff check .
uv run pytest
```

## Local access

The Azure dev Services are `ClusterIP`, not public load balancers. Use
port-forwarding to inspect the frontend locally:

```bash
PATH=/private/tmp/aks-tools:$PATH kubectl -n nucleus port-forward svc/frontend 3000:80
```

Then open:

```text
http://localhost:3000
```
