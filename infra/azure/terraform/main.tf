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
  sku                           = local.deployment_in_vnet ? "Premium" : "Basic"
  admin_enabled                 = false
  public_network_access_enabled = true
  network_rule_set = local.deployment_in_vnet ? [{
    default_action = "Deny"
    ip_rule = [
      for cidr in var.trusted_public_ip_cidrs : {
        action   = "Allow"
        ip_range = cidr
      }
    ]
  }] : []
  tags = local.tags
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

  dynamic "network_rules" {
    for_each = local.deployment_in_vnet ? [1] : []

    content {
      default_action = "Deny"
      bypass         = ["AzureServices"]
      ip_rules       = local.trusted_public_ip_rules
    }
  }

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

resource "azurerm_storage_container" "langfuse" {
  name                  = local.names.langfuse_container
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_management_policy" "main" {
  storage_account_id = azurerm_storage_account.main.id

  rule {
    name    = "expire-langfuse-dev-observability"
    enabled = true

    filters {
      prefix_match = [
        "${local.names.langfuse_container}/events/",
        "${local.names.langfuse_container}/media/",
        "${local.names.langfuse_container}/otel/",
      ]
      blob_types = ["blockBlob"]
    }

    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 30
      }

      snapshot {
        delete_after_days_since_creation_greater_than = 7
      }

      version {
        delete_after_days_since_creation = 7
      }
    }
  }
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

  dynamic "network_acls" {
    for_each = local.deployment_in_vnet ? [1] : []

    content {
      bypass         = "AzureServices"
      default_action = "Deny"
      ip_rules       = local.trusted_public_ip_rules
    }
  }
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

resource "azurerm_key_vault_secret" "langfuse_blob_storage_key" {
  name         = local.names.langfuse_storage_secret
  value        = azurerm_storage_account.main.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
  content_type = "Azure Blob Storage account key for Langfuse"
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
  delegated_subnet_id           = local.deployment_in_vnet ? azurerm_subnet.postgres[0].id : null
  private_dns_zone_id           = local.deployment_in_vnet ? azurerm_private_dns_zone.private_link["postgresql"].id : null
  public_network_access_enabled = !local.deployment_in_vnet
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

  depends_on = [azurerm_private_dns_zone_virtual_network_link.private_link]
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
  count            = local.deployment_in_vnet ? 0 : 1
  name             = local.names.postgres_azure_firewall
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "operator" {
  for_each = local.deployment_in_vnet ? {} : var.postgresql_operator_firewall_rules

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
  authentication_failure_mode   = "http401WithBearerChallenge"
  local_authentication_enabled  = true
  public_network_access_enabled = true
  allowed_ips                   = local.deployment_in_vnet ? local.trusted_public_ip_rules : []
  tags                          = local.tags
}

resource "azapi_resource" "foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-10-01-preview"
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
    properties = merge({
      allowProjectManagement = true
      customSubDomainName    = local.names.foundry_account
      publicNetworkAccess    = "Enabled"
      }, local.deployment_in_vnet ? {
      networkAcls = {
        defaultAction       = "Deny"
        virtualNetworkRules = []
        ipRules = [
          for ip_rule in local.trusted_public_ip_rules : {
            value = ip_rule
          }
        ]
      }
    } : {})
  }

  lifecycle {
    # Azure populates project associations and other read-only properties in
    # the account body. Preserve those service-owned values after import.
    ignore_changes = [body, identity]
  }
}

resource "azapi_resource" "foundry_project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-10-01-preview"
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

  lifecycle {
    # Azure adds default-project and endpoint metadata to the response body.
    ignore_changes = [body, identity]
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
