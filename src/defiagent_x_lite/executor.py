"""Local-only sequential workflow executor and evidence collector.

Separate transactions preserve the contract's explicit approve -> swap -> approve -> deposit
workflow and allow the grader to inspect order, allowances, receipts, and post-state. ERC-20
requires callers to handle false/reverting token operations:
https://eips.ethereum.org/EIPS/eip-20
"""

from __future__ import annotations

from typing import Any, cast

from web3 import Web3
from web3.types import Wei

from .compiler import compile_action
from .constants import POOL, SWAP_ROUTER, USDC, WETH, ZERO_ADDRESS
from .domain import (
    StateObservation,
    SwapAction,
    TransactionObservation,
    WorkflowPlan,
)
from .rpc import ERC20_ABI, VAULT_ABI, WETH_ABI, AnvilClient


def _to_hex_str(value: Any) -> str:
    """Return lowercase 0x-prefixed hex string regardless of input type."""
    if isinstance(value, str):
        s = value.lower()
        return s if s.startswith("0x") else "0x" + s
    if hasattr(value, "hex"):
        h = cast(str, value.hex())
        return h if h.startswith("0x") else "0x" + h
    return "0x" + bytes(value).hex()


def fund_user_with_weth(client: AnvilClient, *, user: str, amount: int) -> None:
    user = Web3.to_checksum_address(user)
    client.set_balance(user, max(client.w3.eth.get_balance(user), amount + 10**20))
    receipt = client.wait(
        client.contract(WETH, WETH_ABI).functions.deposit().transact(
            {"from": user, "value": Wei(amount), "gas": 150_000}
        )
    )
    if receipt["status"] != 1:
        raise RuntimeError("local WETH funding failed")


def execute_plan(client: AnvilClient, *, plan: WorkflowPlan, vault: str | None) -> StateObservation:
    user = Web3.to_checksum_address(plan.user)
    weth = client.contract(WETH, ERC20_ABI)
    usdc = client.contract(USDC, ERC20_ABI)
    vault_contract = client.contract(vault, VAULT_ABI) if vault is not None else None

    weth_before = int(weth.functions.balanceOf(user).call())
    usdc_before = int(usdc.functions.balanceOf(user).call())
    shares_before = (
        int(vault_contract.functions.balanceOf(user).call()) if vault_contract is not None else None
    )
    block_timestamp = int(client.w3.eth.get_block("latest")["timestamp"])
    outputs: dict[str, int] = {}
    observations: list[TransactionObservation] = []
    calldata_matches = True
    unexpected_transfers = False
    transfer_topic = Web3.keccak(text="Transfer(address,address,uint256)").hex().lower().removeprefix("0x")
    monitored_tokens = {WETH.lower(), USDC.lower()}
    if vault is not None:
        monitored_tokens.add(vault.lower())
    allowed_counterparties = {POOL.lower(), ZERO_ADDRESS.lower(), user.lower()}
    if vault is not None:
        allowed_counterparties.add(vault.lower())

    for action in plan.actions:
        compiled = compile_action(
            client=client,
            action=action,
            outputs=outputs,
            block_timestamp=block_timestamp,
        )
        recipient_before: int | None = None
        if isinstance(action, SwapAction):
            recipient_before = int(
                usdc.functions.balanceOf(Web3.to_checksum_address(action.recipient)).call()
            )

        tx_hash = compiled.function.transact({"from": user, "gas": 1_500_000})
        receipt = client.wait(tx_hash)
        transaction = client.w3.eth.get_transaction(tx_hash)
        # Normalize both sides to lowercase 0x-prefixed hex strings. `compiled.data` may be
        # HexBytes or str depending on web3 version; `transaction["input"]` is HexBytes.
        # `_to_hex_str` handles both without raising on str input.
        calldata_matches = calldata_matches and _to_hex_str(transaction["input"]) == _to_hex_str(compiled.data)
        # ERC-20 specifies indexed `from` and `to` fields in Transfer events. Inspecting receipt
        # logs gives the grader observable evidence independent of the guard's plan checks:
        # https://eips.ethereum.org/EIPS/eip-20#events
        for log in receipt["logs"]:
            topics = log["topics"]
            if (
                str(log["address"]).lower() not in monitored_tokens
                or len(topics) < 3
                or topics[0].hex().lower().removeprefix("0x") != transfer_topic
            ):
                continue
            sender = "0x" + topics[1].hex()[-40:]
            receiver = "0x" + topics[2].hex()[-40:]
            if sender.lower() == user.lower() and receiver.lower() not in allowed_counterparties:
                unexpected_transfers = True
            if receiver.lower() == user.lower() and sender.lower() not in allowed_counterparties:
                unexpected_transfers = True

        resolved = compiled.resolved_amount
        if isinstance(action, SwapAction) and receipt["status"] == 1:
            assert recipient_before is not None
            recipient_after = int(
                usdc.functions.balanceOf(Web3.to_checksum_address(action.recipient)).call()
            )
            resolved = recipient_after - recipient_before
            outputs[action.action_id] = resolved

        observations.append(
            TransactionObservation(
                action_id=action.action_id,
                kind=action.kind,
                to=compiled.target,
                sender=user,
                status=int(receipt["status"]),
                gas_used=int(receipt["gasUsed"]),
                transaction_hash=tx_hash.hex(),
                resolved_amount=str(resolved) if resolved is not None else None,
            )
        )
        if receipt["status"] != 1:
            break

    weth_after = int(weth.functions.balanceOf(user).call())
    usdc_after = int(usdc.functions.balanceOf(user).call())
    shares_after = (
        int(vault_contract.functions.balanceOf(user).call()) if vault_contract is not None else None
    )
    usdc_vault_allowance = (
        int(usdc.functions.allowance(user, Web3.to_checksum_address(vault)).call())
        if vault is not None
        else None
    )

    # The independent grader separately checks plan recipients and spenders. This field is
    # reserved for log-derived transfer anomalies and remains false in the Week-4 two-token scope.
    return StateObservation(
        weth_before=str(weth_before),
        weth_after=str(weth_after),
        usdc_before=str(usdc_before),
        usdc_after=str(usdc_after),
        weth_router_allowance_after=str(
            int(weth.functions.allowance(user, Web3.to_checksum_address(SWAP_ROUTER)).call())
        ),
        usdc_vault_allowance_after=(
            str(usdc_vault_allowance) if usdc_vault_allowance is not None else None
        ),
        vault_shares_before=str(shares_before) if shares_before is not None else None,
        vault_shares_after=str(shares_after) if shares_after is not None else None,
        calldata_matches_plan=calldata_matches,
        unexpected_token_transfers=unexpected_transfers,
        transactions=tuple(observations),
    )
