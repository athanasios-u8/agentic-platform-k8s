# Azure development infrastructure

This Terraform root creates the lightweight, public-first Azure foundation for
the `nucleus` development environment in Sweden Central. It does not deploy the
Kubernetes workloads or Helm releases.

## Naming

Resources use:

```text
<resource-type>-<app>-<environment>-<region>-<instance>
```

The dev suffix is `nucleus-dev-swec-001`. Azure resources that prohibit dashes use
the same components without separators:

- AKS: `aks-nucleus-dev-swec-001`
- Existing resource group: `nucleus_swec_dev-rg`
- Container registry: `acrnucleusdevswec001`
- Storage account: `sanucleusdevswec001`

The user-selected `acr` and `sa` prefixes are deliberate project conventions.
Other prefixes follow Microsoft Cloud Adoption Framework abbreviations where a
published abbreviation exists.

## Resources

| Area | Azure resource | Dev name or shape |
|---|---|---|
| Organization | Existing IT-managed resource group | `nucleus_swec_dev-rg` |
| Compute | Azure Kubernetes Service | `aks-nucleus-dev-swec-001`, public API, Free tier |
| AKS infrastructure | AKS-managed node resource group | `rg-nucleus-dev-swec-002` |
| Containers | Azure Container Registry | `acrnucleusdevswec001`, Basic |
| Secrets | Azure Key Vault | `kv-nucleus-dev-swec-001`, RBAC enabled |
| Relational data | Azure Database for PostgreSQL Flexible Server | `psql-nucleus-dev-swec-001`, burstable compute |
| Databases | PostgreSQL databases | `bookstore` and `langfuse` |
| Search | Azure AI Search | `srch-nucleus-dev-swec-001`, Basic |
| Object storage | Storage account and private blob container | `sanucleusdevswec001` / `blob-nucleus-dev-swec-001` |
| AI | Microsoft Foundry account | `aif-nucleus-dev-swec-001` |
| AI | Microsoft Foundry project and model deployment | `proj-nucleus-dev-swec-001` / `model-nucleus-dev-swec-001` |
| Observability | Log Analytics and Application Insights | `log-nucleus-dev-swec-001` / `appi-nucleus-dev-swec-001` |
| Identity | Runtime and indexing managed identities | `id-nucleus-dev-swec-001` / `id-nucleus-dev-swec-002` |
| Identity | Kubernetes workload identity credentials | `fic-nucleus-dev-swec-001` / `fic-nucleus-dev-swec-002` |

Terraform looks up the existing `nucleus_swec_dev-rg` resource group and creates
the application resources inside it. Terraform does not create, rename, retag,
or destroy that resource group. Azure requires AKS node resources to live in a
separate resource group, so AKS creates `rg-nucleus-dev-swec-002`; Terraform
does not create or manage that group independently.

The existing resource group's `env=dev` governance tag is included in the
common Terraform tag map so plans converge without attempting to remove a tag
inherited through Azure governance.

## Connectivity and identity

The dev environment deliberately starts with public service endpoints:

- AKS uses a public API and a Standard public load balancer with one managed
  outbound IP.
- PostgreSQL permits connections from Azure-hosted services through Azure's
  `0.0.0.0` service rule. Optional operator IP ranges can be added in the dev
  tfvars file.
- ACR, Key Vault, AI Search, Storage, and Foundry expose public endpoints.

AKS uses OIDC and workload identity. The runtime identity can read model,
search, blob, and secret data. The indexer identity can additionally update
search indexes and blob data. The AKS kubelet identity receives `AcrPull`.
Terraform generates the PostgreSQL administrator password and stores it in Key
Vault as `sec-nucleus-dev-swec-001`; no secret is committed to the tfvars file.

Local authentication remains enabled for Storage and AI Search during the
bootstrap phase because local repository tooling still supports keys. AI Search
is configured for both API keys and Microsoft Entra authentication so the Azure
AKS Search population and query paths can use workload identities without
requiring Search keys.

## Use

Authenticate with Azure and select the intended subscription before running a
plan. AzureRM 4.x requires the subscription ID to be available to the provider.

```bash
az login
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"

terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform plan \
  -var-file=environments/dev/terraform.tfvars \
  -out=dev.tfplan
terraform -chdir=infra/terraform apply dev.tfplan
```

To remove only Terraform-managed resources, first create and review a destroy
plan, then apply that saved plan. The existing `nucleus_swec_dev-rg` resource
group is a data source and is therefore not part of the destroy plan.

```bash
terraform -chdir=infra/terraform plan \
  -destroy \
  -var-file=environments/dev/terraform.tfvars \
  -out=dev-destroy.tfplan
terraform -chdir=infra/terraform apply dev-destroy.tfplan
```

The current bootstrap uses local Terraform state. Do not commit state or plan
files. Move state to a separately managed remote backend before multiple people
or CI systems apply this configuration.

Foundry model availability, deployment SKU support, and quota vary by region
and subscription. The dev tfvars selects `gpt-5-mini` with
`DataZoneStandard`; Azure verifies that combination during plan and apply.

## Intentionally deferred

To keep dev small, this baseline does not create private endpoints, Private
DNS zones, Azure Firewall, NAT Gateway, Front Door, API Management, managed
Prometheus, Grafana, zone-redundant database compute, or a remote Terraform
state account. Those are hardening and scale steps, not prerequisites for the
first deployment.
