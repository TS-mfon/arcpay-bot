// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Script, console} from "forge-std/Script.sol";
import {ArcPayEscrow} from "../src/ArcPayEscrow.sol";

contract Deploy is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address usdcAddress = vm.envAddress("USDC_CONTRACT_ADDRESS");

        vm.startBroadcast(deployerPrivateKey);

        ArcPayEscrow escrow = new ArcPayEscrow(usdcAddress);

        console.log("ArcPayEscrow deployed at:", address(escrow));
        console.log("USDC address:", usdcAddress);
        console.log("Owner:", escrow.owner());

        vm.stopBroadcast();
    }
}
