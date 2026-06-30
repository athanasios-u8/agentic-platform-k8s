#!/usr/bin/env sh
set -eu

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

if [ -z "${BOOKSTORE_SERVICE_MODULE:-}" ]; then
  echo "BOOKSTORE_SERVICE_MODULE must be set when no command is provided." >&2
  exit 64
fi

exec python -m "$BOOKSTORE_SERVICE_MODULE"
