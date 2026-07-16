output "resource_names" {
  description = "Resolved Azure resource names for this environment."
  value       = local.names
}

output "deployment_in_vnet" {
  value = local.deployment_in_vnet
}

output "resource_group_name" {
  value = data.azurerm_resource_group.main.name
}

output "aks_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "aks_node_resource_group_name" {
  value = azurerm_kubernetes_cluster.main.node_resource_group
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "application_insights_connection_string" {
  value     = azurerm_application_insights.main.connection_string
  sensitive = true
}

output "key_vault_uri" {
  value = azurerm_key_vault.main.vault_uri
}

output "postgresql_fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "existing_vnet_id" {
  value = try(data.azurerm_virtual_network.deployment[0].id, null)
}

output "vnet_subnet_ids" {
  value = local.deployment_in_vnet ? {
    aks               = azurerm_subnet.aks[0].id
    postgres          = azurerm_subnet.postgres[0].id
    private_endpoints = azurerm_subnet.private_endpoints[0].id
    admin             = azurerm_subnet.admin[0].id
  } : {}
}

output "private_dns_zone_names" {
  value = {
    for key, zone in azurerm_private_dns_zone.private_link : key => zone.name
  }
}

output "private_endpoint_ids" {
  value = {
    for key, endpoint in azurerm_private_endpoint.main : key => endpoint.id
  }
}

output "future_nginx_ingress_public_ip" {
  value = try(azurerm_public_ip.future_nginx_ingress[0].ip_address, null)
}

output "postgresql_admin_password_secret_id" {
  value = azurerm_key_vault_secret.postgresql_admin_password.versionless_id
}

output "search_endpoint" {
  value = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "review_storage_container_name" {
  value = azurerm_storage_container.reviews.name
}

output "review_storage_blob_endpoint" {
  value = azurerm_storage_account.main.primary_blob_endpoint
}

output "foundry_account_name" {
  value = azapi_resource.foundry.name
}

output "foundry_project_name" {
  value = azapi_resource.foundry_project.name
}

output "foundry_project_endpoint" {
  value = "https://${local.names.foundry_account}.services.ai.azure.com/api/projects/${local.names.foundry_project}"
}

output "foundry_model_deployment_name" {
  value = azapi_resource.foundry_model.name
}

output "runtime_managed_identity_client_id" {
  value = azurerm_user_assigned_identity.runtime.client_id
}

output "indexer_managed_identity_client_id" {
  value = azurerm_user_assigned_identity.indexer.client_id
}
