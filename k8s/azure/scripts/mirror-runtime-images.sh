#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: mirror-runtime-images.sh [--acr LOGIN_SERVER]

Copies public runtime images used by the Azure KAOS manifests into ACR.

Options:
  --acr LOGIN_SERVER  ACR login server. Defaults to acrnucleusdevswec001.azurecr.io.

Examples:
  k8s/azure/scripts/mirror-runtime-images.sh
  k8s/azure/scripts/mirror-runtime-images.sh --acr acrnucleusdevswec001.azurecr.io
USAGE
}

acr_login_server="acrnucleusdevswec001.azurecr.io"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --acr)
      acr_login_server="${2:?--acr requires a value}"
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

declare -a mirrors=(
  "ghcr.io/berriai/litellm:main-stable|${acr_login_server}/bookstore/litellm:main-stable"
  "ollama/ollama:latest|${acr_login_server}/bookstore/ollama:latest"
  "busybox:1.36.1|${acr_login_server}/bookstore/busybox:1.36.1"
)

for mapping in "${mirrors[@]}"; do
  source_image="${mapping%%|*}"
  target_image="${mapping##*|}"
  echo "Mirroring ${source_image} -> ${target_image}"
  docker buildx imagetools create -t "${target_image}" "${source_image}"
done

echo "Runtime image mirroring complete."
