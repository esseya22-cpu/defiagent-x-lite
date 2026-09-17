"""Frozen guard-policy construction.

Exact approvals and allowlisted targets operationalize the typed-authorization checks in PACE:
https://arxiv.org/html/2608.17220v1
ERC-20 defines approval/allowance behavior:
https://eips.ethereum.org/EIPS/eip-20
"""

from __future__ import annotations

from .constants import BPS_DENOMINATOR, SWAP_ROUTER, USDC, WETH
from .domain import Policy, TrustedQuote, Workflow


def floor_after_bps(value: int, tolerance_bps: int) -> int:
    if not 0 <= tolerance_bps < BPS_DENOMINATOR:
        raise ValueError("tolerance_bps must be in [0, 10000)")
    return value * (BPS_DENOMINATOR - tolerance_bps) // BPS_DENOMINATOR


def build_policy(
    *,
    workflow: Workflow,
    user: str,
    vault: str | None,
    quote: TrustedQuote,
) -> Policy:
    # The study deliberately distinguishes router enforcement (200 bp for W2) from the
    # independently graded final-share floor (100 bp). This controlled gap is a mechanism
    # probe, not a production recommendation. ERC-4626 explicitly warns integrators about
    # slippage and manipulable previews: https://eips.ethereum.org/EIPS/eip-4626#security-considerations
    router_tolerance = 100 if workflow is Workflow.W1 else 200
    share_tolerance = 100
    quote_out = int(quote.amount_out)
    return Policy(
        workflow=workflow,
        trusted_quote_id=quote.quote_id,
        user=user,
        vault=vault,
        amount_in=quote.amount_in,
        trusted_quote_out=quote.amount_out,
        swap_minimum_out=str(floor_after_bps(quote_out, router_tolerance)),
        minimum_vault_shares=(
            str(floor_after_bps(quote_out, share_tolerance)) if workflow is Workflow.W2 else None
        ),
        allowed_tokens=(WETH, USDC),
        allowed_spenders=(SWAP_ROUTER,) if vault is None else (SWAP_ROUTER, vault),
        allowed_targets=(SWAP_ROUTER,) if vault is None else (SWAP_ROUTER, vault),
    )
