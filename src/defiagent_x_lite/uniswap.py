"""Trusted quote and observable pool state adapters.

QuoterV2 and SwapRouter parameter shapes come from the official v3-periphery interfaces:
https://github.com/Uniswap/v3-periphery/blob/main/contracts/interfaces/IQuoterV2.sol
https://github.com/Uniswap/v3-periphery/blob/main/contracts/interfaces/ISwapRouter.sol
"""

from __future__ import annotations

from .canonical import sha256_hex
from .constants import FEE, POOL, QUOTER_V2, USDC, WETH
from .domain import TrustedQuote
from .rpc import POOL_ABI, QUOTER_ABI, AnvilClient


def pool_tick(client: AnvilClient) -> int:
    return int(client.contract(POOL, POOL_ABI).functions.slot0().call()[1])


def trusted_quote(client: AnvilClient, *, amount_in: int, provider_note: str) -> TrustedQuote:
    quoter = client.contract(QUOTER_V2, QUOTER_ABI)
    result = quoter.functions.quoteExactInputSingle((WETH, USDC, amount_in, FEE, 0)).call()
    quote_body = {
        "token_in": WETH,
        "token_out": USDC,
        "fee": FEE,
        "amount_in": str(amount_in),
        "amount_out": str(int(result[0])),
        "block_number": client.w3.eth.block_number,
        "pool_tick": pool_tick(client),
    }
    return TrustedQuote(
        quote_id=sha256_hex(quote_body)[:24],
        provider_note=provider_note,
        **quote_body,
    )

