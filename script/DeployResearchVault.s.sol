// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script} from "forge-std/Script.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ProtocolAddresses} from "../contracts/ProtocolAddresses.sol";
import {ResearchVault} from "../contracts/ResearchVault.sol";

/// @dev Foundry script reference: https://getfoundry.sh/guides/scripting-with-solidity
contract DeployResearchVault is Script {
    function run() external returns (ResearchVault vault) {
        require(block.chainid == ProtocolAddresses.CHAIN_ID, "wrong chain");
        vm.startBroadcast();
        vault = new ResearchVault(IERC20(ProtocolAddresses.USDC));
        vm.stopBroadcast();
    }
}

