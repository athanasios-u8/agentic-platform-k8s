# Azure AKS manifests

This directory contains complete, environment-specific manifests for the Azure
infrastructure created by `infra/terraform`. The dev resources are written in
their final form: namespaces, images, endpoints, managed identity client IDs,
database connections, and Secret references are visible directly in the files.

Kustomize is used only to aggregate files. There are no inherited bases,
patches, replacements, generators, name transforms, or image transforms.

"Complete manifests" does not mean that every resource is a built-in
Kubernetes kind. The application continues to use KAOS `ModelAPI`, `MCPServer`,
and `Agent` custom resources. A target cluster therefore still needs the KAOS
operator and CRDs, the Secrets Store CSI driver with the Azure provider, and
AKS workload identity support.

## Layout

```text
k8s/azure/
├── dev/
│   ├── namespace.yaml             # Namespace
│   ├── serviceaccounts.yaml       # Runtime and indexer workload identities
│   ├── configuration.yaml         # Application config and LiteLLM config Secret
│   ├── key-vault.yaml             # SecretProviderClass and bootstrap Deployment
│   ├── modelapi-*.yaml            # One complete file per ModelAPI
│   ├── mcpserver-*.yaml           # One complete file per MCPServer
│   ├── agent-*.yaml               # One complete file per Agent
│   ├── frontend-gateway.yaml      # Gateway Deployment and Service
│   ├── frontend.yaml              # Frontend Deployment and Service
│   ├── bookstore-secrets.example.yaml
│   └── kustomization.yaml         # resources list only
├── database/dev/
│   ├── job.yaml                   # Complete PostgreSQL population Job
│   └── kustomization.yaml         # resources list only
├── search/dev/
│   ├── job.yaml                   # Complete AI Search population Job
│   └── kustomization.yaml         # resources list only
└── scripts/
    ├── mirror-runtime-images.sh
    ├── populate-postgres.sh
    └── populate-ai-search.sh
```

The command-level deployment record lives in
[`azure-deployment.md`](./azure-deployment.md).

## Dev configuration

The full dev manifests reference the Terraform-provisioned resources directly:

- namespace `nucleus`;
- ACR `acrnucleusdevswec001.azurecr.io` and image tag `dev`;
- PostgreSQL server `psql-nucleus-dev-swec-001.postgres.database.azure.com`;
- AI Search endpoint `https://srch-nucleus-dev-swec-001.search.windows.net`;
- Search index `srch-index-bookstore-dev`;
- Foundry endpoint `https://aif-nucleus-dev-swec-001.openai.azure.com`;
- Foundry deployment `model-nucleus-dev-swec-001`;
- Key Vault `kv-nucleus-dev-swec-001`; and
- the dev runtime and indexer managed identity client IDs.

The duplication is intentional. A reviewer can inspect a workload without
mentally applying a chain of transformations, and each file can be copied or
processed by tools that understand normal Kubernetes YAML.

Application workloads that use the mutable `dev` image tag set
`imagePullPolicy: Always` in the dev manifests. This keeps Azure iteration
predictable after a new image is pushed. For staging and production, prefer
immutable tags or digests and switch back to `IfNotPresent` if desired.

The KAOS LiteLLM ModelAPI, Ollama ModelAPI, and Key Vault bootstrap workloads
also use ACR-hosted runtime images:

- `acrnucleusdevswec001.azurecr.io/bookstore/litellm:main-stable`
- `acrnucleusdevswec001.azurecr.io/bookstore/ollama:latest`
- `acrnucleusdevswec001.azurecr.io/bookstore/busybox:1.36.1`

Mirror those images into ACR before enabling `deployment_in_vnet = true` and
restricting public dependency paths.

```bash
k8s/azure/scripts/mirror-runtime-images.sh
```

## Identities and secrets

`nucleus-runtime` is used by the Foundry-backed LiteLLM ModelAPI, application
agents, Review Summarizer, and the Key Vault bootstrap Deployment. It has
read-only Search data access.

`nucleus-indexer` is reserved for the AI Search population Job. Terraform gives
it Foundry access plus Search Service Contributor and Search Index Data
Contributor permissions.

The PostgreSQL administrator password is never stored in these manifests.
`key-vault.yaml` mounts Key Vault secret `sec-nucleus-dev-swec-001` and
synchronizes it to the namespaced `azure-database-credentials` Secret. Database
consumers reference that Secret and require TLS.

The Azure Search adapter supports API keys for local workflows and
`DefaultAzureCredential` for Azure. The dev manifests enable managed identity,
so Foundry and Search keys are not required in AKS.

`bookstore-secrets` is intentionally excluded from `kustomization.yaml`.
`bookstore-secrets.example.yaml` documents the optional local-key/Tavily shape;
never commit populated values.

## Render and inspect

Render the application resources locally without contacting a cluster:

```bash
kubectl kustomize k8s/azure/dev > /tmp/nucleus-azure-dev.yaml
```

The rendered bundle contains 24 complete resources and no population Job. It
also contains no local PostgreSQL Deployment, Service, or PVC.

Because the source files are already complete, they can also be inspected or
validated individually. The `kustomization.yaml` file only provides a
convenient deterministic bundle.

## Populate Azure PostgreSQL

PostgreSQL population is kept separate because it is destructive. The Job runs
`python -m scripts.reset_demo_data`, which creates missing schema objects,
truncates the bookstore demo tables, resets their identities, and inserts the
synthetic dataset.

Render the full dev Job locally:

```bash
k8s/azure/scripts/populate-postgres.sh --environment dev --render
```

When population is explicitly desired later:

```bash
k8s/azure/scripts/populate-postgres.sh --environment dev
```

The helper displays the active context, namespace, and Job name and requires
the environment name as confirmation. It verifies the PostgreSQL Secret,
replaces only an earlier population Job with the same name, waits for
completion, and prints all container logs.

## Populate Azure AI Search

Run AI Search population after PostgreSQL population. The dev Job creates or
updates the Search index and uploads the checked-in synthetic review seed file
from `data/book_reviews/book_reviews.jsonl` using the indexer workload identity.
This keeps dev population deterministic and avoids coupling deployment to live
review generation. Future environment overlays can switch back to Foundry-backed
generation by running `bookstore-ai-search rebuild` and setting
`BOOK_REVIEW_MIN_REVIEWS`, `BOOK_REVIEW_MAX_REVIEWS`, and
`BOOK_REVIEW_MAX_BOOKS`.

Render the full dev Job locally:

```bash
k8s/azure/scripts/populate-ai-search.sh --environment dev --render
```

When Search population is explicitly desired later:

```bash
k8s/azure/scripts/populate-ai-search.sh --environment dev
```

The helper verifies the PostgreSQL Secret and the annotated
`nucleus-indexer` ServiceAccount. It requires environment confirmation because
the upload changes Search data and some overlays may consume Foundry capacity.
The Job has no automatic retry, avoiding repeated uploads or model generation
after a failure.

Upload uses stable review IDs and upserts matching documents; it does not delete
the Search index first. Catalog entries removed in a later dataset need explicit
Search cleanup if exact replacement is required.

## Add staging and production

Create complete sibling directories instead of introducing overlays:

```text
k8s/azure/staging/
k8s/azure/prod/
k8s/azure/database/staging/
k8s/azure/database/prod/
k8s/azure/search/staging/
k8s/azure/search/prod/
```

Copy the corresponding dev directory, then replace every environment-specific
value directly in the copied manifests:

1. namespace when environments do not share `nucleus`;
2. managed identity client and tenant IDs;
3. Key Vault name and PostgreSQL password object name;
4. PostgreSQL host and administrator;
5. Search endpoint and index name;
6. Foundry endpoint, deployment, and model alias;
7. ACR hostname and immutable image tags; and
8. observability environment labels and any environment-facing URLs.

This deliberately duplicates manifests across environments. The benefit is
that every directory is self-contained, readable, diffable, and portable. Use
render comparison or policy validation in CI to detect accidental drift rather
than reintroducing runtime patch chains.
