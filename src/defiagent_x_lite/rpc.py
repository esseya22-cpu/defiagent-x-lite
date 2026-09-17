"""Strict localhost Anvil client and protocol adapters.

Snapshot/revert and account impersonation are Anvil test-node capabilities:
https://getfoundry.sh/reference/anvil/
They are used only on the disposable pinned fork; the execution URL is checked as loopback twice.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.contract import Contract
from web3.types import TxReceipt

from .config import Settings
from .constants import CHAIN_ID, FACTORY, FORK_BLOCK, POOL, QUOTER_V2, SWAP_ROUTER, USDC, WETH

ERC20_ABI: list[dict[str, Any]] = [
    {"type": "function", "name": "balanceOf", "stateMutability": "view", "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
    {"type": "function", "name": "allowance", "stateMutability": "view", "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
    {"type": "function", "name": "approve", "stateMutability": "nonpayable", "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}]},
]

WETH_ABI: list[dict[str, Any]] = [*ERC20_ABI, {"type": "function", "name": "deposit", "stateMutability": "payable", "inputs": [], "outputs": []}]

FACTORY_ABI: list[dict[str, Any]] = [
    {"type": "function", "name": "getPool", "stateMutability": "view", "inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "fee", "type": "uint24"}], "outputs": [{"name": "pool", "type": "address"}]}
]

POOL_ABI: list[dict[str, Any]] = [
    {"type": "function", "name": "slot0", "stateMutability": "view", "inputs": [], "outputs": [
        {"name": "sqrtPriceX96", "type": "uint160"}, {"name": "tick", "type": "int24"},
        {"name": "observationIndex", "type": "uint16"}, {"name": "observationCardinality", "type": "uint16"},
        {"name": "observationCardinalityNext", "type": "uint16"}, {"name": "feeProtocol", "type": "uint8"},
        {"name": "unlocked", "type": "bool"}
    ]}
]

QUOTER_ABI: list[dict[str, Any]] = [
    {"type": "function", "name": "quoteExactInputSingle", "stateMutability": "nonpayable", "inputs": [{"name": "params", "type": "tuple", "components": [
        {"name": "tokenIn", "type": "address"}, {"name": "tokenOut", "type": "address"},
        {"name": "amountIn", "type": "uint256"}, {"name": "fee", "type": "uint24"},
        {"name": "sqrtPriceLimitX96", "type": "uint160"}
    ]}], "outputs": [
        {"name": "amountOut", "type": "uint256"}, {"name": "sqrtPriceX96After", "type": "uint160"},
        {"name": "initializedTicksCrossed", "type": "uint32"}, {"name": "gasEstimate", "type": "uint256"}
    ]}
]

ROUTER_ABI: list[dict[str, Any]] = [
    {"type": "function", "name": "exactInputSingle", "stateMutability": "payable", "inputs": [{"name": "params", "type": "tuple", "components": [
        {"name": "tokenIn", "type": "address"}, {"name": "tokenOut", "type": "address"},
        {"name": "fee", "type": "uint24"}, {"name": "recipient", "type": "address"},
        {"name": "deadline", "type": "uint256"}, {"name": "amountIn", "type": "uint256"},
        {"name": "amountOutMinimum", "type": "uint256"}, {"name": "sqrtPriceLimitX96", "type": "uint160"}
    ]}], "outputs": [{"name": "amountOut", "type": "uint256"}]}
]

VAULT_ABI: list[dict[str, Any]] = [*ERC20_ABI, {"type": "function", "name": "deposit", "stateMutability": "nonpayable", "inputs": [{"name": "assets", "type": "uint256"}, {"name": "receiver", "type": "address"}], "outputs": [{"name": "shares", "type": "uint256"}]}]


class AnvilClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.w3 = Web3(Web3.HTTPProvider(settings.local_rpc_url, request_kwargs={"timeout": 120}))
        if not self.w3.is_connected():
            raise RuntimeError(f"cannot connect to local Anvil at {settings.local_rpc_url}")

    def rpc(self, method: str, params: list[Any]) -> Any:
        response = self.w3.provider.make_request(method, params)
        if "error" in response:
            raise RuntimeError(f"{method} failed: {response['error']}")
        return response["result"]

    def assert_fixture(self) -> None:
        if self.w3.eth.chain_id != CHAIN_ID:
            raise RuntimeError(f"expected chain id {CHAIN_ID}, got {self.w3.eth.chain_id}")
        if self.w3.eth.block_number < FORK_BLOCK:
            raise RuntimeError("Anvil is not forked at or after the pinned block")
        for address in (WETH, USDC, FACTORY, SWAP_ROUTER, QUOTER_V2, POOL):
            if not self.w3.eth.get_code(Web3.to_checksum_address(address)):
                raise RuntimeError(f"no bytecode at frozen address {address}")
        factory = self.contract(FACTORY, FACTORY_ABI)
        resolved = factory.functions.getPool(WETH, USDC, 3_000).call()
        if resolved.lower() != POOL.lower():
            raise RuntimeError(f"factory pool mismatch: {resolved}")

    def contract(self, address: str, abi: list[dict[str, Any]]) -> Contract:
        return self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)

    def snapshot(self) -> str:
        return str(self.rpc("evm_snapshot", []))

    def revert(self, snapshot_id: str) -> None:
        if not self.rpc("evm_revert", [snapshot_id]):
            raise RuntimeError(f"failed to revert snapshot {snapshot_id}")

    @contextmanager
    def isolated(self) -> Iterator[None]:
        snapshot_id = self.snapshot()
        try:
            yield
        finally:
            self.revert(snapshot_id)

    def set_balance(self, account: str, wei: int) -> None:
        self.rpc("anvil_setBalance", [Web3.to_checksum_address(account), hex(wei)])

    def impersonate(self, account: str) -> None:
        self.rpc("anvil_impersonateAccount", [Web3.to_checksum_address(account)])

    def stop_impersonating(self, account: str) -> None:
        self.rpc("anvil_stopImpersonatingAccount", [Web3.to_checksum_address(account)])

    def wait(self, tx_hash: Any) -> TxReceipt:
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    def deploy_vault(self, sender: str) -> str:
        artifact_path = Path("out/ResearchVault.sol/ResearchVault.json")
        if not artifact_path.exists():
            raise RuntimeError("missing vault artifact; run `forge build` first")
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        bytecode = artifact["bytecode"]["object"]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=bytecode)
        receipt = self.wait(contract.constructor(USDC).transact({"from": sender}))
        if receipt["status"] != 1 or receipt["contractAddress"] is None:
            raise RuntimeError("ResearchVault deployment failed")
        return str(receipt["contractAddress"])

