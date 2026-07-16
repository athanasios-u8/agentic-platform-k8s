#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: populate-ai-search.sh [--environment ENV] [--yes] [--render] [--timeout DURATION]

Creates a one-off Kubernetes Job that reads the PostgreSQL catalog, generates
synthetic reviews with Microsoft Foundry, and creates/updates Azure AI Search.

Options:
  -e, --environment ENV  Environment overlay to use (default: dev)
  -y, --yes              Skip the cost/data-change confirmation
      --render           Render the Job locally without contacting a cluster
      --timeout VALUE    Job completion timeout accepted by kubectl (default: 70m)
  -h, --help             Show this help

Examples:
  k8s/azure/scripts/populate-ai-search.sh --render
  k8s/azure/scripts/populate-ai-search.sh --environment dev
  k8s/azure/scripts/populate-ai-search.sh --environment dev --yes --timeout 90m
EOF
}

environment="dev"
assume_yes="false"
render_only="false"
timeout="70m"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--environment)
      [[ $# -ge 2 ]] || { echo "Missing value for $1." >&2; exit 2; }
      environment="$2"
      shift 2
      ;;
    -y|--yes)
      assume_yes="true"
      shift
      ;;
    --render)
      render_only="true"
      shift
      ;;
    --timeout)
      [[ $# -ge 2 ]] || { echo "Missing value for $1." >&2; exit 2; }
      timeout="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! "$environment" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "Invalid environment name: $environment" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
overlay="$repo_root/k8s/azure/search/$environment"

if [[ ! -f "$overlay/kustomization.yaml" ]]; then
  echo "No AI Search population overlay exists for environment '$environment'." >&2
  echo "Expected: $overlay/kustomization.yaml" >&2
  exit 2
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required." >&2
  exit 127
fi

if [[ "$render_only" == "true" ]]; then
  exec kubectl kustomize "$overlay"
fi

manifest_file="$(mktemp "${TMPDIR:-/tmp}/bookstore-populate-ai-search.XXXXXX.yaml")"
trap 'rm -f "$manifest_file"' EXIT
kubectl kustomize "$overlay" > "$manifest_file"

job_name="$(
  awk '
    /^kind: Job$/ { in_job = 1; next }
    in_job && /^metadata:$/ { in_metadata = 1; next }
    in_job && in_metadata && /^  name:/ { print $2; exit }
  ' "$manifest_file"
)"
namespace="$(
  awk '
    /^kind: Job$/ { in_job = 1; next }
    in_job && /^metadata:$/ { in_metadata = 1; next }
    in_job && in_metadata && /^  namespace:/ { print $2; exit }
  ' "$manifest_file"
)"

if [[ -z "$job_name" || -z "$namespace" ]]; then
  echo "The rendered overlay must contain one namespaced Job." >&2
  exit 2
fi

current_context="$(kubectl config current-context)"

echo "Environment: $environment"
echo "Kubernetes context: $current_context"
echo "Namespace: $namespace"
echo "Job: $job_name"
echo
echo "WARNING: this operation invokes the configured Foundry model and upserts"
echo "synthetic review documents into the environment's Azure AI Search index."

if [[ "$assume_yes" != "true" ]]; then
  if [[ ! -t 0 ]]; then
    echo "Refusing to run without an interactive terminal or --yes." >&2
    exit 3
  fi
  read -r -p "Type '$environment' to continue: " confirmation
  if [[ "$confirmation" != "$environment" ]]; then
    echo "Confirmation did not match; no changes were made." >&2
    exit 3
  fi
fi

if ! kubectl -n "$namespace" get secret azure-database-credentials >/dev/null 2>&1; then
  echo "Secret azure-database-credentials is not available in namespace $namespace." >&2
  echo "Populate/bootstrap PostgreSQL secrets before populating AI Search." >&2
  exit 4
fi

if ! kubectl -n "$namespace" get serviceaccount nucleus-indexer >/dev/null 2>&1; then
  echo "ServiceAccount nucleus-indexer is not available in namespace $namespace." >&2
  echo "Apply the Azure application prerequisites before populating AI Search." >&2
  exit 4
fi

indexer_client_id="$(
  kubectl -n "$namespace" get serviceaccount nucleus-indexer \
    -o jsonpath='{.metadata.annotations.azure\.workload\.identity/client-id}'
)"
if [[ -z "$indexer_client_id" ]]; then
  echo "ServiceAccount nucleus-indexer has no workload identity client ID annotation." >&2
  exit 4
fi

kubectl -n "$namespace" delete job "$job_name" --ignore-not-found --wait=true
kubectl create -f "$manifest_file"

if ! kubectl -n "$namespace" wait \
  --for=condition=complete \
  --timeout="$timeout" \
  "job/$job_name"; then
  echo "AI Search population did not complete successfully." >&2
  kubectl -n "$namespace" logs "job/$job_name" --all-containers=true --prefix=true || true
  exit 5
fi

kubectl -n "$namespace" logs "job/$job_name" --all-containers=true --prefix=true
echo "Azure AI Search population completed for environment '$environment'."
