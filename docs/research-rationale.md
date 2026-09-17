# Week 4 research rationale and code mapping

## Experimental object

The object being evaluated is not Qwen's financial knowledge. It is whether a deterministic
pre-signing mechanism changes execution outcomes when the planner's observation is poisoned or
when execution state differs from planning state. The planner is therefore untrusted, its output
is frozen, and each condition replays the same plan.

PACE supplies the closest DeFi-agent architecture: typed intents, deterministic policy, static and
simulation guards, and the distinction between simulated state S and execution state S-prime.
Source: [PACE](https://arxiv.org/html/2608.17220v1). The code mapping is `domain.py` for the typed
intent, `guards/static.py` for static policy, and `guards/simulation.py` for B2/M/M-E.

AgentDojo supplies the evaluation discipline: matched benign/attacked tasks and deterministic
utility/security functions independent of the model. Source:
[AgentDojo](https://arxiv.org/html/2406.13352). The code mapping is the `pair_id` fields in the
development registry and the separate `oracle.py` plus `grader.py` package boundary.

## Model and prompt

The selected subject is `Qwen/Qwen3-4B-Instruct-2507`, replacing the contract's provisional
Qwen2.5 1.5B choice only after the revision is recorded. The official card identifies it as a
4.0B, Apache-2.0, non-thinking model and reports stronger instruction-following and tool-use
benchmarks than the earlier Qwen3-4B base/non-thinking variant. It also requires Transformers
4.51 or later. Source: [official model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507).

The prompt is deliberately neutral. It asks for a schema-conforming plan but contains no defense
against malicious tool text. Adding an anti-injection instruction would combine a prompt defense
with the mechanism and prevent attribution to the pre-signing guard. The exact prompt is versioned
and hashed. InjecAgent motivates testing attacker instructions embedded in tool/API observations;
source: [InjecAgent](https://arxiv.org/abs/2403.02691).

Outlines is pinned to 0.1.14 because that documented API constrains generation directly from a
Pydantic model. Source: [Outlines JSON generation](https://dottxt-ai.github.io/outlines/0.1.14/reference/generation/json/).
Constrained syntax prevents malformed JSON from dominating Week 4, but it does not constrain the
semantic address or amount choices that the guard is meant to evaluate.

## Protocol and workflows

Uniswap V3 is fixed by the course contract. The original V3 SwapRouter is chosen instead of the
Universal Router because the experiment needs exactly one pool and one `exactInputSingle` ABI;
the smaller action surface reduces irrelevant command/Permit2 confounds. Frozen deployment
addresses come from [Uniswap's Ethereum deployment table](https://developers.uniswap.org/docs/protocols/v3/deployments/v3-ethereum-deployments),
and the pool is re-resolved from the factory at runtime.

W1 exposes recipient, allowance, route, fee, deadline, and minimum-output errors with only two
actions. W2 adds a downstream postcondition: the exact received USDC must be approved and deposited,
and the final share count must meet an independently frozen minimum. ERC-4626 explicitly describes
deposit/share previews and warns that integrators may require a slippage-aware extension; source:
[ERC-4626](https://eips.ethereum.org/EIPS/eip-4626#security-considerations).

The local vault extends OpenZeppelin ERC-4626 and fixes the conversion to one share-unit per asset
unit. This removes yield, fee, exchange-rate, and strategy behavior from the experiment. It is a
fixture, not a production vault. Source: [OpenZeppelin ERC-4626](https://docs.openzeppelin.com/contracts/5.x/erc4626).

## Conditions

| Condition | Information and mechanism | Purpose |
|---|---|---|
| B0 | Valid typed plan only; no policy or simulation | Shows whether a compromised plan can cause an unsafe authorization or recipient outcome |
| B1 | Exact workflow, addresses, amounts, references, fee, deadline, and minima | Separates deterministic structural policy from state reasoning |
| B2 | B1 plus one full workflow simulation at current state S0 | Direct comparator for state drift |
| M-E | The M implementation with only S0 | Code-path ablation |
| M | The same simulation/check path over nine states from −200 to +200 bp | Tests the incremental state-envelope mechanism |

M and M-E share one function. This is necessary for mechanism attribution: their only designed
difference is the state list.

## Envelope construction

The nine preregistered points are −200, −150, −100, −50, 0, +50, +100, +150, and +200 basis points
in the economic USDC price of WETH. Uniswap V3 encodes price geometrically with 1.0001 per tick;
source: [Uniswap V3 whitepaper](https://uniswap.org/whitepaper-v3.pdf). The controller converts the
target price ratio to a target tick, performs actual swaps, and binary-searches the input amount to
within one tick. It never edits the pool's storage.

Nine points do not prove safety between points. They are a bounded empirical grid, and the final
paper must state that limitation.

## Thresholds

W1 uses a 100 bp minimum from the trusted S0 quote. W2 deliberately places the router minimum at
200 bp and the independently graded minimum shares at 100 bp. The gap creates a controlled case in
which a transaction can succeed at the router yet violate the end-to-end W2 utility condition.
This is a mechanism-identification fixture, not recommended production slippage policy.

The sensitivity analysis must note that this one-to-one vault lets a stronger compiler translate
the share requirement into a stricter swap minimum. M's result is therefore limited to the stated
policy representation and fixed plans.

## Evidence and grading

RFC 8785 canonical JSON permits stable plan/policy/prompt hashes:
[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785). JSON Lines keeps each condition execution as an
independent record: [JSON Lines](https://jsonlines.org/). Failed simulation, malformed plan, timeout,
abstention, block, revert, and infrastructure failure must remain explicit categories; none may be
silently removed from denominators.

