app_name    = "nucleus"
environment = "dev"
location    = "Sweden Central"
region_code = "swec"
instance    = "001"

# AKS creates a separate managed resource group for VMSS, NIC, disk, and load
# balancer resources. Azure does not allow these resources in the cluster RG.
node_resource_group_instance = "002"

deployment_in_vnet = true

existing_vnet_name                = "vnet-nucleus-dev-swec-001"
existing_vnet_resource_group_name = "nucleus_swec_dev-rg"
trusted_public_ip_cidrs           = ["20.250.178.236/32"]

vnet_aks_subnet_cidr               = "10.80.0.0/22"
vnet_postgres_subnet_cidr          = "10.80.4.0/24"
vnet_private_endpoints_subnet_cidr = "10.80.5.0/24"
vnet_admin_subnet_cidr             = "10.80.6.0/24"
enable_future_nginx_ingress_ip     = false

aks_kubernetes_version = null
aks_node_vm_size       = "Standard_D4ds_v5"
aks_node_min_count     = 1
aks_node_max_count     = 3

# Public-mode bootstrap settings. These are ignored while deployment_in_vnet is true.
aks_api_server_authorized_ip_ranges = []
postgresql_operator_firewall_rules  = {}

kubernetes_namespace         = "nucleus"
runtime_service_account_name = "nucleus-runtime"
indexer_service_account_name = "nucleus-indexer"

postgresql_version        = "16"
postgresql_sku_name       = "B_Standard_B2ms"
postgresql_storage_mb     = 32768
postgresql_admin_username = "nucleusadmin"

search_sku = "basic"

# Availability and quota are checked by Azure during terraform plan/apply.
foundry_model_name     = "gpt-5-mini"
foundry_model_version  = "2025-08-07"
foundry_model_sku_name = "DataZoneStandard"
foundry_model_capacity = 1

log_analytics_retention_days = 30

tags = {
  architecture = "cloud-native-portable"
  cost-profile = "lightweight"
}
