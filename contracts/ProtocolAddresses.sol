// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @notice Frozen Ethereum addresses for the preregistered block-20,000,000 fixture.
/// @dev Deployment source: https://developers.uniswap.org/docs/protocols/v3/deployments/v3-ethereum-deployments
library ProtocolAddresses {
    uint256 internal constant CHAIN_ID = 1;
    uint256 internal constant FORK_BLOCK = 20_000_000;
    uint24 internal constant FEE = 3000;

    address internal constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address internal constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;
    address internal constant FACTORY = 0x1F98431c8aD98523631AE4a59f267346ea31F984;
    address internal constant SWAP_ROUTER = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    address internal constant QUOTER_V2 = 0x61fFE014bA17989E743c5F6cB21bF9697530B21e;
    address internal constant WETH_USDC_3000_POOL = 0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8;
}

