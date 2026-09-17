// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IQuoterV2} from "../contracts/interfaces/IQuoterV2.sol";
import {ISwapRouter} from "../contracts/interfaces/ISwapRouter.sol";
import {IUniswapV3Factory} from "../contracts/interfaces/IUniswapV3Factory.sol";
import {ProtocolAddresses} from "../contracts/ProtocolAddresses.sol";
import {ResearchVault} from "../contracts/ResearchVault.sol";

/// @notice Archive-backed smoke tests for the exact protocol fixture used by Week 4.
/// @dev Fork testing reference: https://getfoundry.sh/forge/fork-testing
contract Week4ForkGateTest is Test {
    address internal user = makeAddr("week4-user");
    ResearchVault internal vault;

    function setUp() public {
        vm.createSelectFork(vm.envString("FORK_RPC_URL"), ProtocolAddresses.FORK_BLOCK);
        require(block.chainid == ProtocolAddresses.CHAIN_ID, "wrong chain id");
        require(
            IUniswapV3Factory(ProtocolAddresses.FACTORY).getPool(
                ProtocolAddresses.WETH, ProtocolAddresses.USDC, ProtocolAddresses.FEE
            ) == ProtocolAddresses.WETH_USDC_3000_POOL,
            "pool mismatch"
        );
        vault = new ResearchVault(IERC20(ProtocolAddresses.USDC));
    }

    function testPinnedW1ProducesSameOutputTwentyTimes() public {
        uint256 expected;
        for (uint256 i; i < 20; ++i) {
            uint256 snapshot = vm.snapshotState();
            uint256 out = _runW1(0.1 ether);
            if (i == 0) expected = out;
            assertEq(out, expected, "non-deterministic W1 output");
            assertTrue(vm.revertToStateAndDelete(snapshot), "snapshot revert failed");
        }
    }

    function testCleanW1CompletesWithExactApprovalConsumed() public {
        uint256 out = _runW1(0.1 ether);
        assertGt(out, 0);
        assertEq(IERC20(ProtocolAddresses.WETH).allowance(user, ProtocolAddresses.SWAP_ROUTER), 0);
    }

    function testCleanW2CompletesAndMintsMinimumShares() public {
        uint256 out = _runW1(0.1 ether);
        vm.startPrank(user);
        IERC20(ProtocolAddresses.USDC).approve(address(vault), out);
        uint256 shares = vault.deposit(out, user);
        vm.stopPrank();

        assertEq(shares, out, "vault must remain one-to-one");
        assertEq(vault.balanceOf(user), out);
        assertEq(IERC20(ProtocolAddresses.USDC).allowance(user, address(vault)), 0);
    }

    function _runW1(uint256 amountIn) internal returns (uint256 amountOut) {
        // Foundry's token `deal` is a local-fork test primitive, not a mainnet transfer.
        // https://getfoundry.sh/reference/forge-std/deal/
        deal(ProtocolAddresses.WETH, user, amountIn);

        (uint256 quote,,,) = IQuoterV2(ProtocolAddresses.QUOTER_V2).quoteExactInputSingle(
            IQuoterV2.QuoteExactInputSingleParams({
                tokenIn: ProtocolAddresses.WETH,
                tokenOut: ProtocolAddresses.USDC,
                amountIn: amountIn,
                fee: ProtocolAddresses.FEE,
                sqrtPriceLimitX96: 0
            })
        );

        // 100 bp is preregistered as the trusted clean minimum: floor(quote * 0.99).
        uint256 minimum = quote * 9_900 / 10_000;
        vm.startPrank(user);
        IERC20(ProtocolAddresses.WETH).approve(ProtocolAddresses.SWAP_ROUTER, amountIn);
        amountOut = ISwapRouter(ProtocolAddresses.SWAP_ROUTER).exactInputSingle(
            ISwapRouter.ExactInputSingleParams({
                tokenIn: ProtocolAddresses.WETH,
                tokenOut: ProtocolAddresses.USDC,
                fee: ProtocolAddresses.FEE,
                recipient: user,
                deadline: block.timestamp + 300,
                amountIn: amountIn,
                amountOutMinimum: minimum,
                sqrtPriceLimitX96: 0
            })
        );
        vm.stopPrank();
    }
}

