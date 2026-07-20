#!/usr/bin/env bash
set -euo pipefail

readonly script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly namespace="monitoring"
readonly expected_context="aks-nucleus-dev-swec-001"
readonly key_vault_name="kv-nucleus-dev-swec-001"
readonly postgres_password_secret_name="sec-nucleus-dev-swec-001"
readonly blob_storage_key_secret_name="sec-langfuse-blob-nucleus-dev-swec-001"
readonly blob_storage_account_name="sanucleusdevswec001"
readonly helm_chart_version="1.5.39"
readonly retention_days="30"

reset_langfuse_data=false

usage() {
  cat <<'EOF'
Usage: deploy.sh [--reset-langfuse-data]

Deploy Azure dev observability. The optional reset flag irreversibly deletes
the in-cluster Langfuse ClickHouse, Redis, and legacy MinIO data while
preserving the external Azure PostgreSQL database.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reset-langfuse-data)
      reset_langfuse_data=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

for command_name in az kubectl helm openssl python3; do
  require_command "$command_name"
done

current_context="$(kubectl config current-context)"
if [[ "$current_context" != "$expected_context" ]]; then
  echo "Refusing to deploy to Kubernetes context '$current_context'." >&2
  echo "Expected '$expected_context'." >&2
  exit 1
fi

kubectl apply -f "$script_dir/namespace.yaml"

postgres_password="$(
  az keyvault secret show \
    --vault-name "$key_vault_name" \
    --name "$postgres_password_secret_name" \
    --query value \
    --output tsv
)"

if ! kubectl -n "$namespace" get secret langfuse-runtime-secrets >/dev/null 2>&1; then
  salt="$(openssl rand -base64 32 | tr -d '\n')"
  encryption_key="$(openssl rand -hex 32)"
  nextauth_secret="$(openssl rand -base64 32 | tr -d '\n')"
  clickhouse_password="$(openssl rand -base64 32 | tr -d '\n')"
  redis_password="$(openssl rand -base64 32 | tr -d '\n')"
  init_project_public_key="pk-lf-$(openssl rand -hex 16)"
  init_project_secret_key="sk-lf-$(openssl rand -hex 16)"
  init_user_password="$(openssl rand -base64 24 | tr -d '\n')"
  langfuse_auth_string="$(
    printf '%s:%s' "$init_project_public_key" "$init_project_secret_key" | openssl base64 -A
  )"

  kubectl -n "$namespace" create secret generic langfuse-runtime-secrets \
    --from-literal=postgres-password="$postgres_password" \
    --from-literal=salt="$salt" \
    --from-literal=encryption-key="$encryption_key" \
    --from-literal=nextauth-secret="$nextauth_secret" \
    --from-literal=clickhouse-password="$clickhouse_password" \
    --from-literal=redis-password="$redis_password" \
    --from-literal=init-project-public-key="$init_project_public_key" \
    --from-literal=init-project-secret-key="$init_project_secret_key" \
    --from-literal=init-user-password="$init_user_password" \
    --from-literal=langfuse-auth-string="$langfuse_auth_string"
fi

postgres_password_base64="$(printf '%s' "$postgres_password" | openssl base64 -A)"
kubectl -n "$namespace" patch secret langfuse-runtime-secrets \
  --type=merge \
  --patch="{\"data\":{\"postgres-password\":\"${postgres_password_base64}\"}}" \
  >/dev/null
unset postgres_password_base64

blob_storage_key="$(
  az keyvault secret show \
    --vault-name "$key_vault_name" \
    --name "$blob_storage_key_secret_name" \
    --query value \
    --output tsv
)"

kubectl -n "$namespace" create secret generic langfuse-blob-storage \
  --from-literal=account-name="$blob_storage_account_name" \
  --from-literal=account-key="$blob_storage_key" \
  --dry-run=client \
  --output yaml | kubectl apply -f -

unset blob_storage_key

database_url="$(
  POSTGRES_PASSWORD="$postgres_password" python3 -c \
    'import os; from urllib.parse import quote; print("postgresql://nucleusadmin:%s@psql-nucleus-dev-swec-001.postgres.database.azure.com:5432/langfuse?sslmode=require" % quote(os.environ["POSTGRES_PASSWORD"], safe=""))'
)"

kubectl -n "$namespace" create secret generic langfuse-database-url \
  --from-literal=DATABASE_URL="$database_url" \
  --dry-run=client \
  --output yaml | kubectl apply -f -

unset postgres_password database_url

if [[ "$reset_langfuse_data" == true ]]; then
  echo "Resetting disposable Azure dev Langfuse observability data."
  helm uninstall langfuse --namespace "$namespace" --wait --timeout 10m 2>/dev/null || true

  kubectl -n "$namespace" delete pvc \
    --selector app.kubernetes.io/instance=langfuse \
    --ignore-not-found \
    --wait=true

  for legacy_key in minio-root-user minio-root-password; do
    if [[ -n "$(kubectl -n "$namespace" get secret langfuse-runtime-secrets -o "go-template={{ index .data \"${legacy_key}\" }}" 2>/dev/null || true)" ]]; then
      kubectl -n "$namespace" patch secret langfuse-runtime-secrets \
        --type=json \
        --patch="[{\"op\":\"remove\",\"path\":\"/data/${legacy_key}\"}]"
    fi
  done
fi

helm repo add langfuse https://langfuse.github.io/langfuse-k8s --force-update
helm repo update langfuse
helm upgrade --install langfuse langfuse/langfuse \
  --version "$helm_chart_version" \
  --namespace "$namespace" \
  --create-namespace \
  --values "$script_dir/langfuse-values.yaml" \
  --wait \
  --timeout 15m

kubectl apply -k "$script_dir"
kubectl -n "$namespace" rollout status deployment/langfuse-web --timeout=10m
kubectl -n "$namespace" rollout status deployment/langfuse-worker --timeout=10m
kubectl -n "$namespace" rollout status deployment/tempo --timeout=5m
kubectl -n "$namespace" rollout status deployment/grafana --timeout=5m
kubectl -n "$namespace" rollout status deployment/otel-collector --timeout=5m

clickhouse_pod="$(
  kubectl -n "$namespace" get pods \
    --selector app.kubernetes.io/instance=langfuse,app.kubernetes.io/name=clickhouse \
    --field-selector status.phase=Running \
    --output jsonpath='{.items[0].metadata.name}'
)"
clickhouse_password="$(
  kubectl -n "$namespace" get secret langfuse-runtime-secrets \
    -o go-template='{{ index .data "clickhouse-password" }}' | openssl base64 -d -A
)"

kubectl -n "$namespace" exec -i "$clickhouse_pod" -- \
  clickhouse-client \
  --user default \
  --password "$clickhouse_password" \
  --multiquery <<SQL
ALTER TABLE default.traces MODIFY TTL toDateTime(timestamp) + INTERVAL ${retention_days} DAY DELETE;
ALTER TABLE default.observations MODIFY TTL toDateTime(start_time) + INTERVAL ${retention_days} DAY DELETE;
ALTER TABLE default.scores MODIFY TTL toDateTime(timestamp) + INTERVAL ${retention_days} DAY DELETE;
ALTER TABLE default.blob_storage_file_log MODIFY TTL toDateTime(created_at) + INTERVAL ${retention_days} DAY DELETE;
SQL

ttl_table_count="$(
  kubectl -n "$namespace" exec "$clickhouse_pod" -- \
    clickhouse-client \
    --user default \
    --password "$clickhouse_password" \
    --query "SELECT count() FROM system.tables WHERE database = 'default' AND name IN ('traces', 'observations', 'scores', 'blob_storage_file_log') AND position(create_table_query, 'TTL') > 0 FORMAT TSVRaw"
)"
unset clickhouse_password

if [[ "$ttl_table_count" != "4" ]]; then
  echo "Expected retention TTL on four ClickHouse tables; found $ttl_table_count." >&2
  exit 1
fi

echo "Azure dev observability is ready in namespace '$namespace' with ${retention_days}-day retention."
