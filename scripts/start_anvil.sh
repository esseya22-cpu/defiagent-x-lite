#!/usr/bin/env bash
set -euo pipefail

# Provenance: Anvil exposes deterministic fork/block/account configuration.
# https://getfoundry.sh/reference/anvil/
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${FORK_RPC_URL:?FORK_RPC_URL is required}"
: "${FORK_BLOCK:=20000000}"
: "${ANVIL_MNEMONIC:?ANVIL_MNEMONIC is required}"

exec anvil \
  --host 127.0.0.1 \
  --port 8545 \
  --fork-url "${FORK_RPC_URL}" \
  --fork-block-number "${FORK_BLOCK}" \
  --mnemonic "${ANVIL_MNEMONIC}" \
  --chain-id 1 \
  --accounts 10 \
  --balance 10000
