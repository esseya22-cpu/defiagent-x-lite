// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ERC4626} from "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

/// @notice Deliberately simple local research vault; never deploy with real funds.
/// @dev ERC-4626 is used because its deposit/share semantics are standardized:
/// https://eips.ethereum.org/EIPS/eip-4626
/// OpenZeppelin's implementation is pinned by scripts/bootstrap.sh:
/// https://docs.openzeppelin.com/contracts/5.x/erc4626
contract ResearchVault is ERC4626 {
    constructor(IERC20 asset_) ERC20("DeFiAgent-X Research USDC", "dxUSDC") ERC4626(asset_) {}

    /// @dev The experiment specifies exactly one share-unit per USDC base unit and no strategy,
    /// yield, fee, or donation behavior. The override removes exchange-rate drift as a confound.
    function _convertToShares(uint256 assets, Math.Rounding) internal pure override returns (uint256) {
        return assets;
    }

    function _convertToAssets(uint256 shares, Math.Rounding) internal pure override returns (uint256) {
        return shares;
    }
}

