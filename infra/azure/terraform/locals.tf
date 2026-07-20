locals {
  deployment_in_vnet = var.deployment_in_vnet
  suffix             = "${var.app_name}-${var.environment}-${var.region_code}-${var.instance}"
  aks_api_server_authorized_ip_ranges_effective = (
    local.deployment_in_vnet ? var.trusted_public_ip_cidrs : var.aks_api_server_authorized_ip_ranges
  )
  trusted_public_ip_rules = [
    for cidr in var.trusted_public_ip_cidrs : trimsuffix(cidr, "/32")
  ]

  # User-selected abbreviations take precedence where they intentionally differ
  # from the Cloud Adoption Framework list (notably acr and sa).
  names = {
    # Pre-existing IT-managed exception. Keep every other resource modular.
    resource_group             = "nucleus_swec_dev-rg"
    node_resource_group        = "rg-${var.app_name}-${var.environment}-${var.region_code}-${var.node_resource_group_instance}"
    aks                        = "aks-${local.suffix}"
    aks_dns_prefix             = "dns-${local.suffix}"
    aks_node_pool              = "npsystem${var.instance}"
    container_registry         = replace("acr-${local.suffix}", "-", "")
    key_vault                  = "kv-${local.suffix}"
    postgresql                 = "psql-${local.suffix}"
    postgresql_password_secret = "sec-${local.suffix}"
    search                     = "srch-${local.suffix}"
    storage_account            = replace("sa-${local.suffix}", "-", "")
    review_container           = "blob-${local.suffix}"
    langfuse_container         = "langfuse"
    langfuse_storage_secret    = "sec-langfuse-blob-${local.suffix}"
    foundry_account            = "aif-${local.suffix}"
    foundry_project            = "proj-${local.suffix}"
    foundry_model_deployment   = "model-${local.suffix}"
    log_analytics              = "log-${local.suffix}"
    application_insights       = "appi-${local.suffix}"
    runtime_identity           = "id-${local.suffix}"
    indexer_identity           = "id-${var.app_name}-${var.environment}-${var.region_code}-${format("%03d", tonumber(var.instance) + 1)}"
    runtime_federation         = "fic-${local.suffix}"
    indexer_federation         = "fic-${var.app_name}-${var.environment}-${var.region_code}-${format("%03d", tonumber(var.instance) + 1)}"
    postgres_azure_firewall    = "fw-${local.suffix}"
    aks_subnet                 = "snet-aks-${local.suffix}"
    postgres_subnet            = "snet-postgres-${local.suffix}"
    private_endpoints_subnet   = "snet-private-endpoints-${local.suffix}"
    admin_subnet               = "snet-admin-${local.suffix}"
    future_nginx_ingress_ip    = "pip-nginx-ingress-${local.suffix}"
  }

  private_dns_zone_names = {
    acr                = "privatelink.azurecr.io"
    key_vault          = "privatelink.vaultcore.azure.net"
    storage_blob       = "privatelink.blob.core.windows.net"
    search             = "privatelink.search.windows.net"
    cognitive_services = "privatelink.cognitiveservices.azure.com"
    openai             = "privatelink.openai.azure.com"
    ai_services        = "privatelink.services.ai.azure.com"
    postgresql         = "${var.app_name}-${var.environment}-${var.region_code}.postgres.database.azure.com"
  }

  mandatory_tags = {
    application = var.app_name
    env         = var.environment
    environment = var.environment
    region      = var.region_code
    managed-by  = "terraform"
  }

  tags = merge(local.mandatory_tags, var.tags)
}
