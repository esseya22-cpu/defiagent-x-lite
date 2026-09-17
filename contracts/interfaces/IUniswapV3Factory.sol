// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity 0.8.24;

/// Source: https://github.com/Uniswap/v3-core/blob/main/contracts/interfaces/IUniswapV3Factory.sol
interface IUniswapV3Factory {
    function getPool(address tokenA, address tokenB, uint24 fee) external view returns (address pool);
}

