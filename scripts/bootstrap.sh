#!/usr/bin/env bash
set -euo pipefail

# Provenance: Foundry dependency management documents version/tag-pinned installs.
# https://getfoundry.sh/projects/dependencies
if [[ ! -d lib/openzeppelin-contracts ]]; then
  forge install OpenZeppelin/openzeppelin-contracts@v5.4.0 --no-commit
fi

if [[ ! -d lib/forge-std ]]; then
  forge install foundry-rs/forge-std@v1.16.2 --no-commit
fi

expected_openzeppelin="c64a1edb67b6e3f4a15cca8909c9482ad33a02b0"
expected_forge_std="bf647bd6046f2f7da30d0c2bf435e5c76a780c1b"
actual_openzeppelin="$(git -C lib/openzeppelin-contracts rev-parse HEAD)"
actual_forge_std="$(git -C lib/forge-std rev-parse HEAD)"

[[ "$actual_openzeppelin" == "$expected_openzeppelin" ]] || {
  echo "OpenZeppelin revision mismatch: $actual_openzeppelin" >&2
  exit 1
}
[[ "$actual_forge_std" == "$expected_forge_std" ]] || {
  echo "forge-std revision mismatch: $actual_forge_std" >&2
  exit 1
}

uv sync --locked --all-extras --dev
forge build
uv run defiagent-week4 export-schema
