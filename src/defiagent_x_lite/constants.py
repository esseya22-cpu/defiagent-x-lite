"""Frozen experimental constants.

Protocol addresses come from Uniswap's Ethereum deployment documentation:
https://developers.uniswap.org/docs/protocols/v3/deployments/v3-ethereum-deployments
Token addresses are additionally checked at runtime by bytecode and pool-factory queries.
"""

from typing import Final

CHAIN_ID: Final = 1
FORK_BLOCK: Final = 20_000_000
FEE: Final = 3_000

WETH: Final = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC: Final = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
FACTORY: Final = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
SWAP_ROUTER: Final = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
QUOTER_V2: Final = "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"
POOL: Final = "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8"

ZERO_ADDRESS: Final = "0x0000000000000000000000000000000000000000"
BPS_DENOMINATOR: Final = 10_000
DEFAULT_DEADLINE_SECONDS: Final = 300
WETH_DECIMALS: Final = 18
USDC_DECIMALS: Final = 6

# A public exchange hot wallet is used only as an impersonated holder on the disposable fork.
# The doctor command refuses to proceed unless it has sufficient USDC at the pinned block.
# Address provenance: https://etherscan.io/address/0x28c6c06298d514db089934071355e5743bf21d60
USDC_FORK_HOLDER: Final = "0x28C6c06298d514Db089934071355E5743bf21d60"

