# Third-party notices

The top-level `LICENSE` applies to original DeFiAgent-X Lite code. The files
listed below are narrow Solidity interface subsets derived from Uniswap Labs
repositories and retain their upstream `GPL-2.0-or-later` SPDX identifiers.
They are not relicensed under MIT.

| Local file | Upstream project and source | Upstream license |
|---|---|---|
| `contracts/interfaces/IQuoterV2.sol` | [Uniswap v3-periphery, `IQuoterV2.sol`](https://github.com/Uniswap/v3-periphery/blob/main/contracts/interfaces/IQuoterV2.sol) | GPL-2.0-or-later |
| `contracts/interfaces/ISwapRouter.sol` | [Uniswap v3-periphery, `ISwapRouter.sol`](https://github.com/Uniswap/v3-periphery/blob/main/contracts/interfaces/ISwapRouter.sol) | GPL-2.0-or-later |
| `contracts/interfaces/IUniswapV3Factory.sol` | [Uniswap v3-core, `IUniswapV3Factory.sol`](https://github.com/Uniswap/v3-core/blob/main/contracts/interfaces/IUniswapV3Factory.sol) | GPL-2.0-or-later |
| `contracts/interfaces/IUniswapV3PoolState.sol` | [Uniswap v3-core, `IUniswapV3PoolState.sol`](https://github.com/Uniswap/v3-core/blob/main/contracts/interfaces/pool/IUniswapV3PoolState.sol) | GPL-2.0-or-later |

The upstream projects provide their complete license texts here:

- [Uniswap v3-core LICENSE](https://github.com/Uniswap/v3-core/blob/main/LICENSE)
- [Uniswap v3-periphery LICENSE](https://github.com/Uniswap/v3-periphery/blob/main/LICENSE)

OpenZeppelin Contracts and forge-std are consumed as pinned Git submodules and
retain their own upstream licenses and notices. Python packages are installed
from the exact dependency graph in `uv.lock` and retain their respective
upstream licenses.
