# DeFiAgent-X Lite repository rules

## Scope

This repository is a local-only research artifact for one Ethereum mainnet fork at block
20,000,000, one Uniswap V3 WETH/USDC 0.30% pool, and workflows W1 and W2. Do not add live
broadcasting, production wallets, lending, bridges, derivatives, arbitrage, or real funds.

## Non-negotiable safety rules

- `ALLOW_BROADCAST` must remain `0`.
- Execution RPC URLs must resolve to loopback (`127.0.0.1`, `localhost`, or `::1`).
- The archive URL is only an Anvil fork source and is never passed to the planner.
- Never commit `.env`, access tokens, model credentials, private keys, raw secrets, or RPC URLs.
- Never weaken the independent grader to make a guard pass.
- Development scenarios and final frozen scenarios must live in different registries.
- Do not alter pool storage directly. State drift must be produced by actual swaps.

## Required checks

```bash
uv run ruff check src tests
uv run mypy src
uv run pytest
forge fmt --check
forge test
```

## Evidence rule

Every gate run writes canonical JSON records and SHA-256 digests under `results/`. Preserve raw
model text, validated plan, policy digest, condition decision, receipts, state observations,
grader predicates, timing, software versions, and errors. Never record chain of thought.

## Research provenance

The typed-plan and deterministic-policy separation follows PACE:
https://arxiv.org/html/2608.17220v1

The independent deterministic utility/security evaluation and matched clean/attacked cases follow
AgentDojo: https://arxiv.org/html/2406.13352

The local-fork-only boundary follows the course project brief and Foundry fork model:
https://getfoundry.sh/forge/fork-testing

