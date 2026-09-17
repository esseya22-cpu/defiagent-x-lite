"""Bounded Uniswap V3 state construction using real swaps.

Uniswap V3 represents price as ticks where price changes geometrically by 1.0001 per tick:
https://uniswap.org/whitepaper-v3.pdf
The experiment never writes pool storage. It moves the fork state through SwapRouter calls and
binary-searches input size to the preregistered target, preserving protocol semantics.
"""

from __future__ import annotations

import math

from web3 import Web3

from .constants import FEE, SWAP_ROUTER, USDC, USDC_FORK_HOLDER, WETH
from .executor import fund_user_with_weth
from .rpc import ERC20_ABI, ROUTER_ABI, AnvilClient
from .uniswap import pool_tick

ENVELOPE_BPS: tuple[int, ...] = (-200, -150, -100, -50, 0, 50, 100, 150, 200)


def target_tick_for_weth_usdc_bps(base_tick: int, weth_price_bps: int) -> int:
    if not -200 <= weth_price_bps <= 200:
        raise ValueError("state drift must remain within the preregistered +/-200 bp envelope")
    # Pool token0=USDC and token1=WETH, so tick tracks WETH/USDC; the economic USDC/WETH
    # price is its inverse. A positive WETH-USD movement therefore decreases the pool tick.
    ratio = 1.0 + weth_price_bps / 10_000.0
    return base_tick - round(math.log(ratio) / math.log(1.0001))


def _swap_to_move_tick(
    client: AnvilClient,
    *,
    trader: str,
    token_in: str,
    token_out: str,
    amount_in: int,
) -> int:
    trader = Web3.to_checksum_address(trader)
    token = client.contract(token_in, ERC20_ABI)
    approve = client.wait(
        token.functions.approve(Web3.to_checksum_address(SWAP_ROUTER), amount_in).transact(
            {"from": trader, "gas": 150_000}
        )
    )
    if approve["status"] != 1:
        raise RuntimeError("drift approval failed")
    deadline = int(client.w3.eth.get_block("latest")["timestamp"]) + 3_600
    params = (
        Web3.to_checksum_address(token_in),
        Web3.to_checksum_address(token_out),
        FEE,
        trader,
        deadline,
        amount_in,
        0,
        0,
    )
    receipt = client.wait(
        client.contract(SWAP_ROUTER, ROUTER_ABI).functions.exactInputSingle(params).transact(
            {"from": trader, "gas": 1_500_000}
        )
    )
    if receipt["status"] != 1:
        raise RuntimeError("drift swap failed")
    return pool_tick(client)


def apply_tick_drift(client: AnvilClient, *, weth_price_bps: int) -> int:
    if weth_price_bps == 0:
        return pool_tick(client)

    base_tick = pool_tick(client)
    target = target_tick_for_weth_usdc_bps(base_tick, weth_price_bps)
    if weth_price_bps > 0:
        trader = Web3.to_checksum_address(USDC_FORK_HOLDER)
        token_in, token_out = USDC, WETH
        client.impersonate(trader)
        client.set_balance(trader, 10**20)
        balance = int(client.contract(USDC, ERC20_ABI).functions.balanceOf(trader).call())
        maximum = min(balance // 2, 100_000_000 * 10**6)
    else:
        accounts = list(client.w3.eth.accounts)
        if len(accounts) < 2:
            raise RuntimeError(
                "state-drift calibration requires at least two Anvil accounts"
            )
        trader = Web3.to_checksum_address(accounts[1])
        token_in, token_out = WETH, USDC
        maximum = 5_000 * 10**18

    if maximum <= 0:
        raise RuntimeError("drift trader has no input-token balance at the pinned block")

    def trial(amount: int) -> int:
        with client.isolated():
            if token_in.lower() == WETH.lower():
                fund_user_with_weth(client, user=trader, amount=amount)
            return _swap_to_move_tick(
                client,
                trader=trader,
                token_in=token_in,
                token_out=token_out,
                amount_in=amount,
            )

    low, high = 1, maximum
    high_tick = trial(high)
    reached = high_tick <= target if weth_price_bps > 0 else high_tick >= target
    if not reached:
        if weth_price_bps > 0:
            client.stop_impersonating(trader)
        raise RuntimeError(f"cannot reach target tick {target}; maximum-input tick was {high_tick}")

    best_amount, best_error = high, abs(high_tick - target)
    for _ in range(40):
        if low > high:
            break
        middle = (low + high) // 2
        tick = trial(middle)
        error = abs(tick - target)
        if error < best_error:
            best_amount, best_error = middle, error
        if error <= 1:
            best_amount = middle
            break
        if weth_price_bps > 0:
            if tick > target:
                low = middle + 1
            else:
                high = middle - 1
        elif tick < target:
            low = middle + 1
        else:
            high = middle - 1

    if token_in.lower() == WETH.lower():
        fund_user_with_weth(client, user=trader, amount=best_amount)
    final_tick = _swap_to_move_tick(
        client,
        trader=trader,
        token_in=token_in,
        token_out=token_out,
        amount_in=best_amount,
    )
    if weth_price_bps > 0:
        client.stop_impersonating(trader)
    if abs(final_tick - target) > 1:
        raise RuntimeError(f"drift calibration error: target={target}, observed={final_tick}")
    return final_tick

