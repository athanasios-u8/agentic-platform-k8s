#!/usr/bin/env bash
set -euo pipefail

readonly script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly namespace="monitoring"
readonly expected_context="aks-nucleus-dev-swec-001"
readonly key_vault_name="kv-nucleus-dev-swec-001"
readonly postgres_password_secret_name="sec-nucleus-dev-swec-001"
readonly helm_chart_version="1.5.39"

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

if ! kubectl -n "$namespace" get secret langfuse-runtime-secrets >/dev/null 2>&1; then
  postgres_password="$(
    az keyvault secret show \
      --vault-name "$key_vault_name" \
      --name "$postgres_password_secret_name" \
      --query value \
      --output tsv
  )"
  salt="$(openssl rand -base64 32 | tr -d '\n')"
  encryption_key="$(openssl rand -hex 32)"
  nextauth_secret="$(openssl rand -base64 32 | tr -d '\n')"
  clickhouse_password="$(openssl rand -base64 32 | tr -d '\n')"
  redis_password="$(openssl rand -base64 32 | tr -d '\n')"
  minio_root_user="langfuse"
  minio_root_password="$(openssl rand -base64 32 | tr -d '\n')"
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
    --from-literal=minio-root-user="$minio_root_user" \
    --from-literal=minio-root-password="$minio_root_password" \
    --from-literal=init-project-public-key="$init_project_public_key" \
    --from-literal=init-project-secret-key="$init_project_secret_key" \
    --from-literal=init-user-password="$init_user_password" \
    --from-literal=langfuse-auth-string="$langfuse_auth_string"
else
  postgres_password="$(
    kubectl -n "$namespace" get secret langfuse-runtime-secrets \
      -o go-template='{{ index .data "postgres-password" }}' | openssl base64 -d -A
  )"
fi

database_url="$(
  POSTGRES_PASSWORD="$postgres_password" python3 -c \
    'import os; from urllib.parse import quote; print("postgresql://nucleusadmin:%s@psql-nucleus-dev-swec-001.postgres.database.azure.com:5432/langfuse?sslmode=require" % quote(os.environ["POSTGRES_PASSWORD"], safe=""))'
)"

kubectl -n "$namespace" create secret generic langfuse-database-url \
  --from-literal=DATABASE_URL="$database_url" \
  --dry-run=client \
  --output yaml | kubectl apply -f -

unset postgres_password database_url

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

echo "Azure dev observability deployment is ready in namespace '$namespace'."
