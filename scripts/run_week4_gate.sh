#!/usr/bin/env bash
set -euo pipefail

# Gate order is deliberate: cheap static checks precede archive-backed experiments.
uv run ruff check src tests
uv run mypy src
uv run pytest
forge fmt --check
forge test --match-contract Week4ForkGateTest -vv
uv run defiagent-week4 doctor
uv run defiagent-week4 gate --planner qwen --repetitions 20

