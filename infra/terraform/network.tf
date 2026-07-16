data "azurerm_virtual_network" "deployment" {
  count               = local.deployment_in_vnet ? 1 : 0
  name                = var.existing_vnet_name
  resource_group_name = var.existing_vnet_resource_group_name
}

resource "azurerm_subnet" "aks" {
  count                = local.deployment_in_vnet ? 1 : 0
  name                 = local.names.aks_subnet
  resource_group_name  = data.azurerm_virtual_network.deployment[0].resource_group_name
  virtual_network_name = data.azurerm_virtual_network.deployment[0].name
  address_prefixes     = [var.vnet_aks_subnet_cidr]
}

resource "azurerm_subnet" "postgres" {
  count                = local.deployment_in_vnet ? 1 : 0
  name                 = local.names.postgres_subnet
  resource_group_name  = data.azurerm_virtual_network.deployment[0].resource_group_name
  virtual_network_name = data.azurerm_virtual_network.deployment[0].name
  address_prefixes     = [var.vnet_postgres_subnet_cidr]
  service_endpoints    = ["Microsoft.Storage"]

  delegation {
    name = "postgresql-flexible-server"

    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

resource "azurerm_subnet" "private_endpoints" {
  count                = local.deployment_in_vnet ? 1 : 0
  name                 = local.names.private_endpoints_subnet
  resource_group_name  = data.azurerm_virtual_network.deployment[0].resource_group_name
  virtual_network_name = data.azurerm_virtual_network.deployment[0].name
  address_prefixes     = [var.vnet_private_endpoints_subnet_cidr]
}

resource "azurerm_subnet" "admin" {
  count                = local.deployment_in_vnet ? 1 : 0
  name                 = local.names.admin_subnet
  resource_group_name  = data.azurerm_virtual_network.deployment[0].resource_group_name
  virtual_network_name = data.azurerm_virtual_network.deployment[0].name
  address_prefixes     = [var.vnet_admin_subnet_cidr]
}

resource "azurerm_private_dns_zone" "private_link" {
  for_each            = local.deployment_in_vnet ? local.private_dns_zone_names : {}
  name                = each.value
  resource_group_name = data.azurerm_resource_group.main.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "private_link" {
  for_each              = local.deployment_in_vnet ? local.private_dns_zone_names : {}
  name                  = "lnk-${replace(each.key, "_", "-")}-${local.suffix}"
  private_dns_zone_name = azurerm_private_dns_zone.private_link[each.key].name
  resource_group_name   = data.azurerm_resource_group.main.name
  virtual_network_id    = data.azurerm_virtual_network.deployment[0].id
  registration_enabled  = false
  tags                  = local.tags
}

locals {
  private_endpoint_targets = {
    acr = {
      name                  = "pe-acr-${local.suffix}"
      resource_id           = azurerm_container_registry.main.id
      subresource_names     = ["registry"]
      private_dns_zone_keys = ["acr"]
    }
    key_vault = {
      name                  = "pe-kv-${local.suffix}"
      resource_id           = azurerm_key_vault.main.id
      subresource_names     = ["vault"]
      private_dns_zone_keys = ["key_vault"]
    }
    storage_blob = {
      name                  = "pe-blob-${local.suffix}"
      resource_id           = azurerm_storage_account.main.id
      subresource_names     = ["blob"]
      private_dns_zone_keys = ["storage_blob"]
    }
    search = {
      name                  = "pe-search-${local.suffix}"
      resource_id           = azurerm_search_service.main.id
      subresource_names     = ["searchService"]
      private_dns_zone_keys = ["search"]
    }
    foundry = {
      name              = "pe-foundry-${local.suffix}"
      resource_id       = azapi_resource.foundry.id
      subresource_names = ["account"]
      private_dns_zone_keys = [
        "cognitive_services",
        "openai",
        "ai_services",
      ]
    }
  }
}

resource "azurerm_private_endpoint" "main" {
  for_each            = local.deployment_in_vnet ? local.private_endpoint_targets : {}
  name                = each.value.name
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.private_endpoints[0].id
  tags                = local.tags

  private_service_connection {
    name                           = "psc-${each.key}-${local.suffix}"
    is_manual_connection           = false
    private_connection_resource_id = each.value.resource_id
    subresource_names              = each.value.subresource_names
  }

  private_dns_zone_group {
    name = "default"
    private_dns_zone_ids = [
      for zone_key in each.value.private_dns_zone_keys : azurerm_private_dns_zone.private_link[zone_key].id
    ]
  }

  depends_on = [
    azurerm_container_registry.main,
    azurerm_key_vault.main,
    azurerm_storage_account.main,
    azurerm_search_service.main,
    azapi_resource.foundry,
    azurerm_private_dns_zone_virtual_network_link.private_link,
  ]
}

resource "azurerm_public_ip" "future_nginx_ingress" {
  count               = local.deployment_in_vnet && var.enable_future_nginx_ingress_ip ? 1 : 0
  name                = local.names.future_nginx_ingress_ip
  location            = data.azurerm_resource_group.main.location
  resource_group_name = azurerm_kubernetes_cluster.main.node_resource_group
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tags
}
