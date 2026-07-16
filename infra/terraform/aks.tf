resource "azurerm_kubernetes_cluster" "main" {
  name                = local.names.aks
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  node_resource_group = local.deployment_in_vnet ? "${local.names.node_resource_group}-vnet" : local.names.node_resource_group
  dns_prefix          = local.names.aks_dns_prefix
  kubernetes_version  = var.aks_kubernetes_version
  sku_tier            = "Free"
  support_plan        = "KubernetesOfficial"

  private_cluster_enabled           = false
  role_based_access_control_enabled = true
  local_account_disabled            = true
  oidc_issuer_enabled               = true
  workload_identity_enabled         = true
  azure_policy_enabled              = false
  image_cleaner_enabled             = true
  image_cleaner_interval_hours      = 48
  automatic_upgrade_channel         = "patch"
  node_os_upgrade_channel           = "NodeImage"

  default_node_pool {
    name                 = local.names.aks_node_pool
    vm_size              = var.aks_node_vm_size
    auto_scaling_enabled = true
    min_count            = var.aks_node_min_count
    max_count            = var.aks_node_max_count
    node_count           = var.aks_node_min_count
    max_pods             = 50
    os_disk_size_gb      = 128
    os_disk_type         = "Managed"
    type                 = "VirtualMachineScaleSets"
    vnet_subnet_id       = local.deployment_in_vnet ? azurerm_subnet.aks[0].id : null
    zones                = []

    upgrade_settings {
      max_surge = "33%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  azure_active_directory_role_based_access_control {
    azure_rbac_enabled = true
    tenant_id          = data.azurerm_client_config.current.tenant_id
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_data_plane  = "cilium"
    load_balancer_sku   = "standard"
    outbound_type       = "loadBalancer"
    pod_cidr            = "10.244.0.0/16"
    service_cidr        = "10.2.0.0/16"
    dns_service_ip      = "10.2.0.10"

    load_balancer_profile {
      managed_outbound_ip_count = 1
    }
  }

  oms_agent {
    log_analytics_workspace_id      = azurerm_log_analytics_workspace.main.id
    msi_auth_for_monitoring_enabled = true
  }

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  dynamic "api_server_access_profile" {
    for_each = length(local.aks_api_server_authorized_ip_ranges_effective) == 0 ? [] : [1]

    content {
      authorized_ip_ranges = local.aks_api_server_authorized_ip_ranges_effective
    }
  }

  tags = local.tags
}

resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                            = azurerm_container_registry.main.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "terraform_aks_cluster_admin" {
  scope                = azurerm_kubernetes_cluster.main.id
  role_definition_name = "Azure Kubernetes Service RBAC Cluster Admin"
  principal_id         = data.azurerm_client_config.current.object_id
}
