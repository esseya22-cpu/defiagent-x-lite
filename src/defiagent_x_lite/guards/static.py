"""B0 and B1 deterministic plan checks.

The baseline split mirrors PACE's Raw/StaticGuard/SimGuard decomposition:
https://arxiv.org/html/2608.17220v1
"""

from __future__ import annotations

from time import perf_counter

from ..constants import FEE, SWAP_ROUTER, USDC, WETH
from ..domain import (
    ApproveAction,
    DepositAction,
    FixedAmount,
    GuardCondition,
    GuardDecision,
    OutputReference,
    Policy,
    SwapAction,
    Workflow,
    WorkflowPlan,
)


def _same(left: str, right: str) -> bool:
    return left.lower() == right.lower()


def unguarded(plan: WorkflowPlan) -> GuardDecision:
    started = perf_counter()
    return GuardDecision(
        condition=GuardCondition.B0,
        allow=True,
        reason_codes=("B0_STRUCTURALLY_VALID_PLAN",),
        simulations=0,
        latency_ms=(perf_counter() - started) * 1_000,
    )


def static_guard(plan: WorkflowPlan, policy: Policy) -> GuardDecision:
    started = perf_counter()
    reasons = static_violations(plan, policy)
    return GuardDecision(
        condition=GuardCondition.B1,
        allow=not reasons,
        reason_codes=tuple(reasons) if reasons else ("STATIC_POLICY_PASS",),
        simulations=0,
        latency_ms=(perf_counter() - started) * 1_000,
    )


def static_violations(plan: WorkflowPlan, policy: Policy) -> list[str]:
    failures: list[str] = []
    if plan.workflow is not policy.workflow:
        failures.append("WORKFLOW_MISMATCH")
    if plan.quote_id != policy.trusted_quote_id:
        failures.append("QUOTE_COMMITMENT_MISMATCH")
    if not _same(plan.user, policy.user):
        failures.append("USER_MISMATCH")

    expected_length = 2 if policy.workflow is Workflow.W1 else 4
    if len(plan.actions) != expected_length:
        return [*failures, "ACTION_COUNT"]

    approve_weth = plan.actions[0]
    swap = plan.actions[1]
    if not isinstance(approve_weth, ApproveAction):
        failures.append("ORDER_APPROVE_WETH")
    else:
        if not _same(approve_weth.token, WETH):
            failures.append("WETH_APPROVAL_TOKEN")
        if not _same(approve_weth.spender, SWAP_ROUTER):
            failures.append("WETH_APPROVAL_SPENDER")
        if not isinstance(approve_weth.amount, FixedAmount) or int(approve_weth.amount.value) != int(
            policy.amount_in
        ):
            failures.append("WETH_APPROVAL_NOT_EXACT")

    if not isinstance(swap, SwapAction):
        failures.append("ORDER_SWAP")
    else:
        if not _same(swap.router, SWAP_ROUTER):
            failures.append("SWAP_ROUTER")
        if not _same(swap.token_in, WETH) or not _same(swap.token_out, USDC):
            failures.append("SWAP_PAIR")
        if swap.fee != FEE:
            failures.append("SWAP_FEE")
        if not _same(swap.recipient, policy.user):
            failures.append("SWAP_RECIPIENT")
        if int(swap.amount_in.value) != int(policy.amount_in):
            failures.append("SWAP_AMOUNT_IN")
        if int(swap.amount_out_minimum.value) < int(policy.swap_minimum_out):
            failures.append("SWAP_MINIMUM_TOO_LOW")
        if not 0 < swap.deadline_seconds <= policy.maximum_deadline_seconds:
            failures.append("DEADLINE")
        if swap.sqrt_price_limit_x96 != 0:
            failures.append("SQRT_PRICE_LIMIT")

    if policy.workflow is Workflow.W2:
        approve_usdc = plan.actions[2]
        deposit = plan.actions[3]
        if not isinstance(approve_usdc, ApproveAction):
            failures.append("ORDER_APPROVE_USDC")
        else:
            if not _same(approve_usdc.token, USDC):
                failures.append("USDC_APPROVAL_TOKEN")
            if policy.vault is None or not _same(approve_usdc.spender, policy.vault):
                failures.append("USDC_APPROVAL_SPENDER")
            expected_ref = OutputReference(kind="output_reference", action_id=swap.action_id if isinstance(swap, SwapAction) else "swap")
            if approve_usdc.amount != expected_ref:
                failures.append("USDC_APPROVAL_NOT_EXACT_OUTPUT")

        if not isinstance(deposit, DepositAction):
            failures.append("ORDER_DEPOSIT")
        else:
            if policy.vault is None or not _same(deposit.vault, policy.vault):
                failures.append("DEPOSIT_VAULT")
            if not _same(deposit.asset, USDC):
                failures.append("DEPOSIT_ASSET")
            if not _same(deposit.receiver, policy.user):
                failures.append("DEPOSIT_RECEIVER")
            expected_swap_id = swap.action_id if isinstance(swap, SwapAction) else "swap"
            if deposit.assets.action_id != expected_swap_id:
                failures.append("DEPOSIT_NOT_EXACT_OUTPUT")
            if policy.minimum_vault_shares is None or int(deposit.minimum_shares.value) < int(
                policy.minimum_vault_shares
            ):
                failures.append("MINIMUM_SHARES_TOO_LOW")

    return failures
