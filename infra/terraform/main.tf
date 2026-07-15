data "azurerm_resource_group" "main" {
  name = local.names.resource_group
}

resource "azurerm_log_analytics_workspace" "main" {
  name                       = local.names.log_analytics
  location                   = data.azurerm_resource_group.main.location
  resource_group_name        = data.azurerm_resource_group.main.name
  sku                        = "PerGB2018"
  retention_in_days          = var.log_analytics_retention_days
  internet_ingestion_enabled = true
  internet_query_enabled     = true
  tags                       = local.tags
}

resource "azurerm_application_insights" "main" {
  name                = local.names.application_insights
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.main.id
  tags                = local.tags
}

resource "azurerm_container_registry" "main" {
  name                          = local.names.container_registry
  resource_group_name           = data.azurerm_resource_group.main.name
  location                      = data.azurerm_resource_group.main.location
  sku                           = "Basic"
  admin_enabled                 = false
  public_network_access_enabled = true
  tags                          = local.tags
}

resource "azurerm_storage_account" "main" {
  name                            = local.names.storage_account
  resource_group_name             = data.azurerm_resource_group.main.name
  location                        = data.azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  access_tier                     = "Hot"
  min_tls_version                 = "TLS1_2"
  public_network_access_enabled   = true
  shared_access_key_enabled       = true
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  tags                            = local.tags

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }
}

resource "azurerm_storage_container" "reviews" {
  name                  = local.names.review_container
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_key_vault" "main" {
  name                          = local.names.key_vault
  location                      = data.azurerm_resource_group.main.location
  resource_group_name           = data.azurerm_resource_group.main.name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  public_network_access_enabled = true
  purge_protection_enabled      = false
  soft_delete_retention_days    = 7
  tags                          = local.tags
}

resource "azurerm_role_assignment" "terraform_key_vault_secrets_officer" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "random_password" "postgresql_admin" {
  length           = 32
  min_lower        = 4
  min_numeric      = 4
  min_special      = 4
  min_upper        = 4
  override_special = "!#$%&*+-=?@^_"
}

resource "azurerm_key_vault_secret" "postgresql_admin_password" {
  name         = local.names.postgresql_password_secret
  value        = random_password.postgresql_admin.result
  key_vault_id = azurerm_key_vault.main.id
  content_type = "PostgreSQL administrator password"
  tags         = local.tags

  depends_on = [azurerm_role_assignment.terraform_key_vault_secrets_officer]
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                          = local.names.postgresql
  resource_group_name           = data.azurerm_resource_group.main.name
  location                      = data.azurerm_resource_group.main.location
  version                       = var.postgresql_version
  administrator_login           = var.postgresql_admin_username
  administrator_password        = random_password.postgresql_admin.result
  public_network_access_enabled = true
  sku_name                      = var.postgresql_sku_name
  storage_mb                    = var.postgresql_storage_mb
  auto_grow_enabled             = true
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  tags                          = local.tags

  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = true
    tenant_id                     = data.azurerm_client_config.current.tenant_id
  }

  lifecycle {
    ignore_changes = [zone]
  }
}

resource "azurerm_postgresql_flexible_server_database" "bookstore" {
  name      = "bookstore"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_database" "langfuse" {
  name      = "langfuse"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# The 0.0.0.0 rule allows connections from Azure-hosted services. It is the
# smallest practical public-network bootstrap for AKS without pre-allocating a
# fixed egress IP. Replace it with explicit egress ranges when networking is
# hardened.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = local.names.postgres_azure_firewall
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "operator" {
  for_each = var.postgresql_operator_firewall_rules

  name             = each.key
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = each.value.start_ip_address
  end_ip_address   = each.value.end_ip_address
}

resource "azurerm_search_service" "main" {
  name                          = local.names.search
  resource_group_name           = data.azurerm_resource_group.main.name
  location                      = data.azurerm_resource_group.main.location
  sku                           = var.search_sku
  replica_count                 = 1
  partition_count               = 1
  local_authentication_enabled  = true
  public_network_access_enabled = true
  tags                          = local.tags
}

resource "azapi_resource" "foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-06-01"
  name      = local.names.foundry_account
  parent_id = data.azurerm_resource_group.main.id
  location  = data.azurerm_resource_group.main.location
  tags      = local.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "AIServices"
    sku = {
      name = "S0"
    }
    properties = {
      allowProjectManagement = true
      customSubDomainName    = local.names.foundry_account
      publicNetworkAccess    = "Enabled"
    }
  }
}

resource "azapi_resource" "foundry_project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  name      = local.names.foundry_project
  parent_id = azapi_resource.foundry.id
  location  = data.azurerm_resource_group.main.location
  tags      = local.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = {
      displayName = "Nucleus ${upper(var.environment)}"
      description = "Nucleus agentic platform ${var.environment} project"
    }
  }
}

resource "azapi_resource" "foundry_model" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2023-05-01"
  name      = local.names.foundry_model_deployment
  parent_id = azapi_resource.foundry.id

  body = {
    sku = {
      name     = var.foundry_model_sku_name
      capacity = var.foundry_model_capacity
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = var.foundry_model_name
        version = var.foundry_model_version
      }
      versionUpgradeOption = "OnceNewDefaultVersionAvailable"
    }
  }
}
