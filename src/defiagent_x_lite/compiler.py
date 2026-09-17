"""Trusted compiler from typed plan actions to ABI calls.

The model never emits raw calldata. PACE's typed intent/policy split motivates compiling only
after validation: https://arxiv.org/html/2608.17220v1
ABI shapes are sourced from the official Uniswap interfaces and ERC standards, not model text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from web3 import Web3

from .domain import ApproveAction, DepositAction, FixedAmount, OutputReference, SwapAction
from .rpc import ERC20_ABI, ROUTER_ABI, VAULT_ABI, AnvilClient


@dataclass(frozen=True)
class CompiledCall:
    action_id: str
    kind: str
    target: str
    function: Any
    data: str
    resolved_amount: int | None = None


def _address(value: str) -> str:
    return Web3.to_checksum_address(value)


def resolve_amount(value: FixedAmount | OutputReference, outputs: dict[str, int]) -> int:
    if isinstance(value, FixedAmount):
        return int(value.value)
    try:
        return outputs[value.action_id]
    except KeyError as exc:
        raise ValueError(f"unresolved output reference {value.action_id}") from exc


def compile_action(
    *,
    client: AnvilClient,
    action: ApproveAction | SwapAction | DepositAction,
    outputs: dict[str, int],
    block_timestamp: int,
) -> CompiledCall:
    if isinstance(action, ApproveAction):
        amount = resolve_amount(action.amount, outputs)
        function = client.contract(action.token, ERC20_ABI).functions.approve(
            _address(action.spender), amount
        )
        return CompiledCall(
            action_id=action.action_id,
            kind=action.kind,
            target=_address(action.token),
            function=function,
            data=function._encode_transaction_data(),
            resolved_amount=amount,
        )
    if isinstance(action, SwapAction):
        params = (
            _address(action.token_in),
            _address(action.token_out),
            action.fee,
            _address(action.recipient),
            block_timestamp + action.deadline_seconds,
            int(action.amount_in.value),
            int(action.amount_out_minimum.value),
            action.sqrt_price_limit_x96,
        )
        function = client.contract(action.router, ROUTER_ABI).functions.exactInputSingle(params)
        return CompiledCall(
            action_id=action.action_id,
            kind=action.kind,
            target=_address(action.router),
            function=function,
            data=function._encode_transaction_data(),
        )

    amount = resolve_amount(action.assets, outputs)
    function = client.contract(action.vault, VAULT_ABI).functions.deposit(
        amount, _address(action.receiver)
    )
    return CompiledCall(
        action_id=action.action_id,
        kind=action.kind,
        target=_address(action.vault),
        function=function,
        data=function._encode_transaction_data(),
        resolved_amount=amount,
    )

