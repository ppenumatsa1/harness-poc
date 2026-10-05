#!/bin/bash
# The host's ~/.azure is mounted read-only at /azure-host. The az CLI needs a writable
# config dir (token cache refresh), so copy it into the container's own AZURE_CONFIG_DIR.
set -euo pipefail
if [ -d /azure-host ]; then
  mkdir -p "$AZURE_CONFIG_DIR"
  # Copy only what `az account get-access-token` needs (the full dir can be hundreds of MB).
  for f in azureProfile.json msal_token_cache.json msal_http_cache.bin config clouds.config az.json az.sess; do
    [ -f "/azure-host/$f" ] && cp "/azure-host/$f" "$AZURE_CONFIG_DIR/"
  done
fi
exec "$@"
