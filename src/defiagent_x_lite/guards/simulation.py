"""B2, M-E, and M state simulation guards.

PACE identifies current-state simulation's limitation when execution state differs from simulated
state: https://arxiv.org/html/2608.17220v1
M varies only the state set; it reuses this exact simulation/checking path, making M-E a code-path
ablation rather than a second implementation.
"""

from __future__ import annotations

from time import perf_counter

from ..domain import GuardCondition, GuardDecision, Policy, Workflow, WorkflowPlan
from ..executor import execute_plan
from ..rpc import AnvilClient
from ..state_drift import ENVELOPE_BPS, apply_tick_drift
from .static import static_violations


def _postconditions_pass(*, observation: object, policy: Policy) -> tuple[bool, str]:
    # Local import keeps the guard independent from the grader module while retaining types.
    from ..domain import StateObservation

    if not isinstance(observation, StateObservation):
        return False, "SIMULATION_INTERNAL_TYPE"
    if len(observation.transactions) == 0 or any(tx.status != 1 for tx in observation.transactions):
        return False, "SIMULATION_REVERT"
    swaps = [tx for tx in observation.transactions if tx.kind == "swap_exact_input_single"]
    if len(swaps) != 1 or swaps[0].resolved_amount is None:
        return False, "SIMULATION_MISSING_SWAP_OUTPUT"
    if int(swaps[0].resolved_amount) < int(policy.swap_minimum_out):
        return False, "SIMULATION_MINIMUM_OUTPUT"
    if int(observation.weth_router_allowance_after) != 0:
        return False, "SIMULATION_WETH_ALLOWANCE"
    if policy.workflow is Workflow.W2:
        if observation.vault_shares_before is None or observation.vault_shares_after is None:
            return False, "SIMULATION_MISSING_SHARES"
        minted = int(observation.vault_shares_after) - int(observation.vault_shares_before)
        if policy.minimum_vault_shares is None or minted < int(policy.minimum_vault_shares):
            return False, "SIMULATION_MINIMUM_SHARES"
        if observation.usdc_vault_allowance_after is None or int(
            observation.usdc_vault_allowance_after
        ) != 0:
            return False, "SIMULATION_USDC_ALLOWANCE"
    return True, "SIMULATION_PASS"


def simulation_guard(
    *,
    client: AnvilClient,
    plan: WorkflowPlan,
    policy: Policy,
    vault: str | None,
    condition: GuardCondition,
) -> GuardDecision:
    if condition not in {GuardCondition.B2, GuardCondition.M, GuardCondition.M_E}:
        raise ValueError("simulation_guard only implements B2, M, and M-E")
    started = perf_counter()
    static_failures = static_violations(plan, policy)
    if static_failures:
        return GuardDecision(
            condition=condition,
            allow=False,
            reason_codes=tuple(static_failures),
            simulations=0,
            latency_ms=(perf_counter() - started) * 1_000,
        )

    states = ENVELOPE_BPS if condition is GuardCondition.M else (0,)
    observed_ticks: list[int] = []
    reason = "SIMULATION_PASS"
    simulations = 0
    for drift_bps in states:
        with client.isolated():
            tick = apply_tick_drift(client, weth_price_bps=drift_bps)
            observed_ticks.append(tick)
            observation = execute_plan(client, plan=plan, vault=vault)
            simulations += 1
            passed, state_reason = _postconditions_pass(observation=observation, policy=policy)
            if not passed:
                reason = f"{state_reason}@{drift_bps:+d}bp"
                break

    return GuardDecision(
        condition=condition,
        allow=reason == "SIMULATION_PASS",
        reason_codes=(reason,),
        simulations=simulations,
        latency_ms=(perf_counter() - started) * 1_000,
        state_ticks=tuple(observed_ticks),
    )

