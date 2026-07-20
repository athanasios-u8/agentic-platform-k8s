resource "azurerm_user_assigned_identity" "runtime" {
  name                = local.names.runtime_identity
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "indexer" {
  name                = local.names.indexer_identity
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = local.tags
}

resource "azurerm_federated_identity_credential" "runtime" {
  name                      = local.names.runtime_federation
  user_assigned_identity_id = azurerm_user_assigned_identity.runtime.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = azurerm_kubernetes_cluster.main.oidc_issuer_url
  subject                   = "system:serviceaccount:${var.kubernetes_namespace}:${var.runtime_service_account_name}"
}

resource "azurerm_federated_identity_credential" "indexer" {
  name                      = local.names.indexer_federation
  user_assigned_identity_id = azurerm_user_assigned_identity.indexer.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = azurerm_kubernetes_cluster.main.oidc_issuer_url
  subject                   = "system:serviceaccount:${var.kubernetes_namespace}:${var.indexer_service_account_name}"
}

resource "azurerm_role_assignment" "runtime_foundry_user" {
  scope                            = azapi_resource.foundry.id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = azurerm_user_assigned_identity.runtime.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "runtime_search_reader" {
  scope                            = azurerm_search_service.main.id
  role_definition_name             = "Search Index Data Reader"
  principal_id                     = azurerm_user_assigned_identity.runtime.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "runtime_blob_reader" {
  scope                            = azurerm_storage_account.main.id
  role_definition_name             = "Storage Blob Data Reader"
  principal_id                     = azurerm_user_assigned_identity.runtime.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "runtime_key_vault_reader" {
  scope                            = azurerm_key_vault.main.id
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = azurerm_user_assigned_identity.runtime.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "indexer_foundry_user" {
  scope                            = azapi_resource.foundry.id
  role_definition_name             = "Cognitive Services OpenAI User"
  principal_id                     = azurerm_user_assigned_identity.indexer.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "indexer_search_data_contributor" {
  scope                            = azurerm_search_service.main.id
  role_definition_name             = "Search Index Data Contributor"
  principal_id                     = azurerm_user_assigned_identity.indexer.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "indexer_search_service_contributor" {
  scope                            = azurerm_search_service.main.id
  role_definition_name             = "Search Service Contributor"
  principal_id                     = azurerm_user_assigned_identity.indexer.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "indexer_blob_contributor" {
  scope                            = azurerm_storage_account.main.id
  role_definition_name             = "Storage Blob Data Contributor"
  principal_id                     = azurerm_user_assigned_identity.indexer.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "indexer_key_vault_reader" {
  scope                            = azurerm_key_vault.main.id
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = azurerm_user_assigned_identity.indexer.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "aks_key_vault_reader" {
  scope                            = azurerm_key_vault.main.id
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = azurerm_kubernetes_cluster.main.key_vault_secrets_provider[0].secret_identity[0].object_id
  skip_service_principal_aad_check = true
}
