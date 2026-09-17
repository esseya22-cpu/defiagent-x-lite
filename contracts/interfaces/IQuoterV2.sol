// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity 0.8.24;

/// @dev Source-compatible subset of Uniswap V3 IQuoterV2.
/// Source: https://github.com/Uniswap/v3-periphery/blob/main/contracts/interfaces/IQuoterV2.sol
interface IQuoterV2 {
    struct QuoteExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint256 amountIn;
        uint24 fee;
        uint160 sqrtPriceLimitX96;
    }

    function quoteExactInputSingle(QuoteExactInputSingleParams memory params)
        external
        returns (uint256 amountOut, uint160 sqrtPriceX96After, uint32 initializedTicksCrossed, uint256 gasEstimate);
}

