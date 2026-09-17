"""Deterministic reference-plan construction for chain reproducibility tests.

This builder is not an experimental agent and is never counted as a model result. It isolates
fork determinism from model variability, as required by the Week-4 gate.
"""

from __future__ import annotations

from .constants import CHAIN_ID, FEE, FORK_BLOCK, SWAP_ROUTER, USDC, WETH
from .domain import (
    ApproveAction,
    DepositAction,
    FixedAmount,
    OutputReference,
    Policy,
    SwapAction,
    TrustedQuote,
    Workflow,
    WorkflowPlan,
)


def reference_plan(*, quote: TrustedQuote, policy: Policy) -> WorkflowPlan:
    approve_weth = ApproveAction(
        kind="approve",
        action_id="approve_weth",
        token=WETH,
        spender=SWAP_ROUTER,
        amount=FixedAmount(kind="fixed", value=policy.amount_in),
    )
    swap = SwapAction(
        kind="swap_exact_input_single",
        action_id="swap",
        router=SWAP_ROUTER,
        token_in=WETH,
        token_out=USDC,
        fee=FEE,
        recipient=policy.user,
        amount_in=FixedAmount(kind="fixed", value=policy.amount_in),
        amount_out_minimum=FixedAmount(kind="fixed", value=policy.swap_minimum_out),
        deadline_seconds=policy.maximum_deadline_seconds,
        sqrt_price_limit_x96=0,
    )
    actions: list[ApproveAction | SwapAction | DepositAction] = [approve_weth, swap]
    if policy.workflow is Workflow.W2:
        if policy.vault is None or policy.minimum_vault_shares is None:
            raise ValueError("W2 policy requires vault and minimum shares")
        output = OutputReference(kind="output_reference", action_id="swap")
        actions.extend(
            [
                ApproveAction(
                    kind="approve",
                    action_id="approve_usdc",
                    token=USDC,
                    spender=policy.vault,
                    amount=output,
                ),
                DepositAction(
                    kind="deposit_erc4626",
                    action_id="deposit",
                    vault=policy.vault,
                    asset=USDC,
                    receiver=policy.user,
                    assets=output,
                    minimum_shares=FixedAmount(kind="fixed", value=policy.minimum_vault_shares),
                ),
            ]
        )
    return WorkflowPlan(
        workflow=policy.workflow,
        chain_id=CHAIN_ID,
        fork_block=FORK_BLOCK,
        user=policy.user,
        quote_id=quote.quote_id,
        actions=tuple(actions),
    )

