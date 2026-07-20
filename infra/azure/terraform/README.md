# Azure development infrastructure

This Terraform root creates the Azure foundation for the `nucleus` development
environment in Sweden Central. It supports two deployment modes through one
switch:

```hcl
deployment_in_vnet = true  # secure mode using an existing VNet
deployment_in_vnet = false # public/bootstrap mode
```

It does not deploy the Kubernetes workloads or Helm releases.

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
| AKS infrastructure | AKS-managed node resource group | `rg-nucleus-dev-swec-002`, or `rg-nucleus-dev-swec-002-vnet` in VNet mode |
| Network | Existing VNet input for secure mode | `vnet-nucleus-dev-swec-001`, `10.80.0.0/16` |
| Containers | Azure Container Registry | `acrnucleusdevswec001`, Basic in public mode, Premium in VNet mode |
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

When `deployment_in_vnet = true`, Terraform also looks up an existing VNet
named `vnet-nucleus-dev-swec-001`. Terraform does not create, retag, or change
the VNet address space. It only creates subnets, Private DNS zones, Private
Endpoints, and network settings inside or alongside that existing VNet.

The existing resource group's `env=dev` governance tag is included in the
common Terraform tag map so plans converge without attempting to remove a tag
inherited through Azure governance.

## Connectivity modes

### Public mode: `deployment_in_vnet = false`

This preserves the original public/bootstrap behavior. Override
`deployment_in_vnet = false` when you explicitly want the older public shape.

- AKS uses a public API and a Standard public load balancer with one managed
  outbound IP.
- PostgreSQL permits connections from Azure-hosted services through Azure's
  `0.0.0.0` service rule. Optional operator IP ranges can be added in the dev
  tfvars file.
- ACR, Key Vault, AI Search, Storage, and Foundry expose public endpoints.

No VNet data source, subnets, Private DNS zones, Private Endpoints, or reserved
future ingress IP are created in this mode.

### Secure VNet mode: `deployment_in_vnet = true`

Before enabling this mode, create the VNet manually:

```bash
az network vnet create \
  --resource-group nucleus_swec_dev-rg \
  --location swedencentral \
  --name vnet-nucleus-dev-swec-001 \
  --address-prefixes 10.80.0.0/16
```

Terraform then creates these subnets inside that VNet:

| Subnet | CIDR | Purpose |
|---|---:|---|
| `snet-aks-nucleus-dev-swec-001` | `10.80.0.0/22` | AKS nodes |
| `snet-postgres-nucleus-dev-swec-001` | `10.80.4.0/24` | PostgreSQL Flexible Server delegated subnet |
| `snet-private-endpoints-nucleus-dev-swec-001` | `10.80.5.0/24` | Private Endpoints |
| `snet-admin-nucleus-dev-swec-001` | `10.80.6.0/24` | Reserved for future admin tooling |

In VNet mode:

- AKS is rebuilt with its default node pool in the AKS subnet.
- AKS API access is restricted to `20.250.178.236/32`.
- PostgreSQL is rebuilt with private VNet integration and public network access
  disabled.
- ACR is upgraded to Premium so Private Link can be used.
- Private Endpoints and Private DNS zones are created for ACR, Key Vault,
  Storage Blob, Azure AI Search, and Foundry/Cognitive Services.
- Remaining public data-plane access for local administration is restricted to
  the trusted public IP list.
- A Standard static public IP can be reserved in the AKS node resource group for
  a future allowlisted NGINX ingress when `enable_future_nginx_ingress_ip` is
  enabled. Dev keeps this disabled because it is not needed for the current
  ClusterIP plus port-forward access path.

Switching modes can replace AKS and PostgreSQL. This is acceptable for dev, but
it means data must be repopulated after a VNet-mode rebuild.

## Identity

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

terraform -chdir=infra/azure/terraform init
terraform -chdir=infra/azure/terraform plan \
  -var-file=environments/dev/terraform.tfvars \
  -out=dev.tfplan
terraform -chdir=infra/azure/terraform apply dev.tfplan
```

To preview public mode while `dev.tfvars` is set to private mode, override the
switch:

```bash
terraform -chdir=infra/azure/terraform plan \
  -var-file=environments/dev/terraform.tfvars \
  -var='deployment_in_vnet=false'
```

To remove only Terraform-managed resources, first create and review a destroy
plan, then apply that saved plan. The existing `nucleus_swec_dev-rg` resource
group is a data source and is therefore not part of the destroy plan.

```bash
terraform -chdir=infra/azure/terraform plan \
  -destroy \
  -var-file=environments/dev/terraform.tfvars \
  -out=dev-destroy.tfplan
terraform -chdir=infra/azure/terraform apply dev-destroy.tfplan
```

The current bootstrap uses local Terraform state. Do not commit state or plan
files. Move state to a separately managed remote backend before multiple people
or CI systems apply this configuration.

Foundry model availability, deployment SKU support, and quota vary by region
and subscription. The dev tfvars selects `gpt-5-mini` with
`DataZoneStandard`; Azure verifies that combination during plan and apply.

## Intentionally deferred

This root still does not create Azure Firewall, NAT Gateway, Front Door, API
Management, managed Prometheus, Grafana, zone-redundant database compute, or a
remote Terraform state account. Those are hardening and scale steps beyond the
optional VNet/Private Link deployment.
