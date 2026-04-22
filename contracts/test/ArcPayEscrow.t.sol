// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Test, console} from "forge-std/Test.sol";
import {ArcPayEscrow} from "../src/ArcPayEscrow.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @dev Mock USDC token for testing
contract MockUSDC is ERC20 {
    constructor() ERC20("USD Coin", "USDC") {}

    function decimals() public pure override returns (uint8) {
        return 6;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract ArcPayEscrowTest is Test {
    ArcPayEscrow public escrow;
    MockUSDC public usdc;

    address public alice = makeAddr("alice");
    address public bob = makeAddr("bob");
    address public charlie = makeAddr("charlie");
    address public owner = makeAddr("owner");

    uint256 constant AMOUNT = 100 * 1e6; // 100 USDC

    function setUp() public {
        vm.startPrank(owner);
        usdc = new MockUSDC();
        escrow = new ArcPayEscrow(address(usdc));
        vm.stopPrank();

        // Mint USDC to test users
        usdc.mint(alice, 10_000 * 1e6);
        usdc.mint(bob, 10_000 * 1e6);
        usdc.mint(charlie, 10_000 * 1e6);

        // Approve escrow to spend tokens
        vm.prank(alice);
        usdc.approve(address(escrow), type(uint256).max);

        vm.prank(bob);
        usdc.approve(address(escrow), type(uint256).max);

        vm.prank(charlie);
        usdc.approve(address(escrow), type(uint256).max);
    }

    // -------------------------------------------------------------------------
    // Constructor
    // -------------------------------------------------------------------------

    function test_constructor() public view {
        assertEq(address(escrow.usdc()), address(usdc));
        assertEq(escrow.owner(), owner);
        assertEq(escrow.nextRequestId(), 0);
        assertEq(escrow.defaultExpiry(), 7 days);
    }

    function test_constructor_zeroAddress() public {
        vm.expectRevert(ArcPayEscrow.ZeroAddress.selector);
        new ArcPayEscrow(address(0));
    }

    // -------------------------------------------------------------------------
    // sendPayment
    // -------------------------------------------------------------------------

    function test_sendPayment() public {
        uint256 aliceBefore = usdc.balanceOf(alice);
        uint256 bobBefore = usdc.balanceOf(bob);

        vm.prank(alice);
        vm.expectEmit(true, true, false, true);
        emit ArcPayEscrow.PaymentSent(alice, bob, AMOUNT, "lunch");
        escrow.sendPayment(bob, AMOUNT, "lunch");

        assertEq(usdc.balanceOf(alice), aliceBefore - AMOUNT);
        assertEq(usdc.balanceOf(bob), bobBefore + AMOUNT);
    }

    function test_sendPayment_zeroAmount() public {
        vm.prank(alice);
        vm.expectRevert(ArcPayEscrow.ZeroAmount.selector);
        escrow.sendPayment(bob, 0, "");
    }

    function test_sendPayment_zeroAddress() public {
        vm.prank(alice);
        vm.expectRevert(ArcPayEscrow.ZeroAddress.selector);
        escrow.sendPayment(address(0), AMOUNT, "");
    }

    // -------------------------------------------------------------------------
    // batchSendPayment
    // -------------------------------------------------------------------------

    function test_batchSendPayment() public {
        address[] memory recipients = new address[](2);
        recipients[0] = bob;
        recipients[1] = charlie;

        uint256[] memory amounts = new uint256[](2);
        amounts[0] = 50 * 1e6;
        amounts[1] = 50 * 1e6;

        uint256 aliceBefore = usdc.balanceOf(alice);

        vm.prank(alice);
        escrow.batchSendPayment(recipients, amounts, "dinner split");

        assertEq(usdc.balanceOf(alice), aliceBefore - 100 * 1e6);
        assertEq(usdc.balanceOf(bob), 10_000 * 1e6 + 50 * 1e6);
        assertEq(usdc.balanceOf(charlie), 10_000 * 1e6 + 50 * 1e6);
    }

    function test_batchSendPayment_lengthMismatch() public {
        address[] memory recipients = new address[](2);
        recipients[0] = bob;
        recipients[1] = charlie;

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = 50 * 1e6;

        vm.prank(alice);
        vm.expectRevert(ArcPayEscrow.ArrayLengthMismatch.selector);
        escrow.batchSendPayment(recipients, amounts, "");
    }

    // -------------------------------------------------------------------------
    // createRequest
    // -------------------------------------------------------------------------

    function test_createRequest() public {
        vm.prank(alice);
        vm.expectEmit(true, true, true, false);
        emit ArcPayEscrow.RequestCreated(0, alice, bob, AMOUNT, "rent", 0);
        uint256 requestId = escrow.createRequest(bob, AMOUNT, "rent");

        assertEq(requestId, 0);
        assertEq(escrow.nextRequestId(), 1);

        ArcPayEscrow.PaymentRequest memory req = escrow.getRequest(0);
        assertEq(req.requester, alice);
        assertEq(req.payer, bob);
        assertEq(req.amount, AMOUNT);
        assertEq(keccak256(bytes(req.reason)), keccak256(bytes("rent")));
        assertEq(uint256(req.status), uint256(ArcPayEscrow.RequestStatus.Pending));
    }

    function test_createRequest_zeroAddress() public {
        vm.prank(alice);
        vm.expectRevert(ArcPayEscrow.ZeroAddress.selector);
        escrow.createRequest(address(0), AMOUNT, "rent");
    }

    function test_createRequest_zeroAmount() public {
        vm.prank(alice);
        vm.expectRevert(ArcPayEscrow.ZeroAmount.selector);
        escrow.createRequest(bob, 0, "rent");
    }

    // -------------------------------------------------------------------------
    // fulfillRequest
    // -------------------------------------------------------------------------

    function test_fulfillRequest() public {
        vm.prank(alice);
        uint256 requestId = escrow.createRequest(bob, AMOUNT, "rent");

        uint256 aliceBefore = usdc.balanceOf(alice);
        uint256 bobBefore = usdc.balanceOf(bob);

        vm.prank(bob);
        vm.expectEmit(true, true, true, true);
        emit ArcPayEscrow.RequestFulfilled(requestId, bob, alice, AMOUNT);
        escrow.fulfillRequest(requestId);

        assertEq(usdc.balanceOf(alice), aliceBefore + AMOUNT);
        assertEq(usdc.balanceOf(bob), bobBefore - AMOUNT);

        ArcPayEscrow.PaymentRequest memory req = escrow.getRequest(requestId);
        assertEq(uint256(req.status), uint256(ArcPayEscrow.RequestStatus.Fulfilled));
    }

    function test_fulfillRequest_notPayer() public {
        vm.prank(alice);
        uint256 requestId = escrow.createRequest(bob, AMOUNT, "rent");

        vm.prank(charlie);
        vm.expectRevert(ArcPayEscrow.NotRequestPayer.selector);
        escrow.fulfillRequest(requestId);
    }

    function test_fulfillRequest_expired() public {
        vm.prank(alice);
        uint256 requestId = escrow.createRequest(bob, AMOUNT, "rent");

        // Fast-forward past expiry
        vm.warp(block.timestamp + 8 days);

        vm.prank(bob);
        vm.expectRevert(ArcPayEscrow.RequestExpired.selector);
        escrow.fulfillRequest(requestId);
    }

    function test_fulfillRequest_alreadyFulfilled() public {
        vm.prank(alice);
        uint256 requestId = escrow.createRequest(bob, AMOUNT, "rent");

        vm.prank(bob);
        escrow.fulfillRequest(requestId);

        vm.prank(bob);
        vm.expectRevert(ArcPayEscrow.RequestNotPending.selector);
        escrow.fulfillRequest(requestId);
    }

    // -------------------------------------------------------------------------
    // cancelRequest
    // -------------------------------------------------------------------------

    function test_cancelRequest() public {
        vm.prank(alice);
        uint256 requestId = escrow.createRequest(bob, AMOUNT, "rent");

        vm.prank(alice);
        vm.expectEmit(true, false, false, false);
        emit ArcPayEscrow.RequestCancelled(requestId);
        escrow.cancelRequest(requestId);

        ArcPayEscrow.PaymentRequest memory req = escrow.getRequest(requestId);
        assertEq(uint256(req.status), uint256(ArcPayEscrow.RequestStatus.Cancelled));
    }

    function test_cancelRequest_notRequester() public {
        vm.prank(alice);
        uint256 requestId = escrow.createRequest(bob, AMOUNT, "rent");

        vm.prank(bob);
        vm.expectRevert(ArcPayEscrow.NotRequestRequester.selector);
        escrow.cancelRequest(requestId);
    }

    // -------------------------------------------------------------------------
    // isExpired
    // -------------------------------------------------------------------------

    function test_isExpired_false() public {
        vm.prank(alice);
        uint256 requestId = escrow.createRequest(bob, AMOUNT, "rent");

        assertFalse(escrow.isExpired(requestId));
    }

    function test_isExpired_true() public {
        vm.prank(alice);
        uint256 requestId = escrow.createRequest(bob, AMOUNT, "rent");

        vm.warp(block.timestamp + 8 days);
        assertTrue(escrow.isExpired(requestId));
    }

    // -------------------------------------------------------------------------
    // setDefaultExpiry
    // -------------------------------------------------------------------------

    function test_setDefaultExpiry() public {
        vm.prank(owner);
        escrow.setDefaultExpiry(14 days);
        assertEq(escrow.defaultExpiry(), 14 days);
    }

    function test_setDefaultExpiry_zeroReverts() public {
        vm.prank(owner);
        vm.expectRevert(ArcPayEscrow.InvalidExpiry.selector);
        escrow.setDefaultExpiry(0);
    }

    function test_setDefaultExpiry_notOwner() public {
        vm.prank(alice);
        vm.expectRevert();
        escrow.setDefaultExpiry(14 days);
    }

    // -------------------------------------------------------------------------
    // createRequestWithExpiry
    // -------------------------------------------------------------------------

    function test_createRequestWithExpiry() public {
        vm.prank(alice);
        uint256 requestId = escrow.createRequestWithExpiry(
            bob,
            AMOUNT,
            "rent",
            1 days
        );

        ArcPayEscrow.PaymentRequest memory req = escrow.getRequest(requestId);
        assertEq(req.expiresAt, block.timestamp + 1 days);
    }

    function test_createRequestWithExpiry_zeroReverts() public {
        vm.prank(alice);
        vm.expectRevert(ArcPayEscrow.InvalidExpiry.selector);
        escrow.createRequestWithExpiry(bob, AMOUNT, "rent", 0);
    }
}
