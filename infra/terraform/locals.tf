locals {
  suffix = "${var.app_name}-${var.environment}-${var.region_code}-${var.instance}"

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
