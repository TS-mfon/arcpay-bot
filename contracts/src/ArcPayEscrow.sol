// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title ArcPayEscrow
/// @notice Payment escrow and request fulfillment for the ArcPay Telegram bot
/// @dev Uses USDC (IERC20) for all payments. Supports direct sends, payment
///      requests with expiry, and batch operations for group splits.
contract ArcPayEscrow is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // -------------------------------------------------------------------------
    // Types
    // -------------------------------------------------------------------------

    enum RequestStatus {
        Pending,
        Fulfilled,
        Cancelled,
        Expired
    }

    struct PaymentRequest {
        uint256 id;
        address requester;
        address payer;
        uint256 amount;
        string reason;
        uint256 expiresAt;
        RequestStatus status;
        uint256 createdAt;
    }

    // -------------------------------------------------------------------------
    // State
    // -------------------------------------------------------------------------

    IERC20 public immutable usdc;

    uint256 public nextRequestId;

    /// @notice requestId => PaymentRequest
    mapping(uint256 => PaymentRequest) public requests;

    /// @notice Default request expiry duration (7 days)
    uint256 public defaultExpiry = 7 days;

    // -------------------------------------------------------------------------
    // Events
    // -------------------------------------------------------------------------

    event PaymentSent(
        address indexed from,
        address indexed to,
        uint256 amount,
        string memo
    );

    event RequestCreated(
        uint256 indexed requestId,
        address indexed requester,
        address indexed payer,
        uint256 amount,
        string reason,
        uint256 expiresAt
    );

    event RequestFulfilled(
        uint256 indexed requestId,
        address indexed payer,
        address indexed requester,
        uint256 amount
    );

    event RequestCancelled(uint256 indexed requestId);

    event DefaultExpiryUpdated(uint256 newExpiry);

    // -------------------------------------------------------------------------
    // Errors
    // -------------------------------------------------------------------------

    error ZeroAmount();
    error ZeroAddress();
    error RequestNotFound();
    error RequestNotPending();
    error NotRequestPayer();
    error NotRequestRequester();
    error RequestExpired();
    error InvalidExpiry();
    error ArrayLengthMismatch();

    // -------------------------------------------------------------------------
    // Constructor
    // -------------------------------------------------------------------------

    /// @param _usdc Address of the USDC token contract
    constructor(address _usdc) Ownable(msg.sender) {
        if (_usdc == address(0)) revert ZeroAddress();
        usdc = IERC20(_usdc);
    }

    // -------------------------------------------------------------------------
    // Direct Payments
    // -------------------------------------------------------------------------

    /// @notice Send USDC directly to another address
    /// @param to Recipient address
    /// @param amount Amount of USDC (6 decimals)
    /// @param memo Optional memo string
    function sendPayment(
        address to,
        uint256 amount,
        string calldata memo
    ) external nonReentrant {
        if (to == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();

        usdc.safeTransferFrom(msg.sender, to, amount);

        emit PaymentSent(msg.sender, to, amount, memo);
    }

    /// @notice Send USDC to multiple recipients (for splits)
    /// @param recipients Array of recipient addresses
    /// @param amounts Array of amounts corresponding to each recipient
    /// @param memo Shared memo for the batch
    function batchSendPayment(
        address[] calldata recipients,
        uint256[] calldata amounts,
        string calldata memo
    ) external nonReentrant {
        if (recipients.length != amounts.length) revert ArrayLengthMismatch();

        for (uint256 i = 0; i < recipients.length; i++) {
            if (recipients[i] == address(0)) revert ZeroAddress();
            if (amounts[i] == 0) revert ZeroAmount();

            usdc.safeTransferFrom(msg.sender, recipients[i], amounts[i]);

            emit PaymentSent(msg.sender, recipients[i], amounts[i], memo);
        }
    }

    // -------------------------------------------------------------------------
    // Payment Requests
    // -------------------------------------------------------------------------

    /// @notice Create a payment request
    /// @param payer Address expected to pay
    /// @param amount Amount of USDC requested
    /// @param reason Reason for the request
    /// @return requestId The ID of the created request
    function createRequest(
        address payer,
        uint256 amount,
        string calldata reason
    ) external returns (uint256 requestId) {
        return createRequestWithExpiry(payer, amount, reason, defaultExpiry);
    }

    /// @notice Create a payment request with custom expiry
    /// @param payer Address expected to pay
    /// @param amount Amount of USDC requested
    /// @param reason Reason for the request
    /// @param expiryDuration Duration in seconds until expiry
    /// @return requestId The ID of the created request
    function createRequestWithExpiry(
        address payer,
        uint256 amount,
        string calldata reason,
        uint256 expiryDuration
    ) public returns (uint256 requestId) {
        if (payer == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        if (expiryDuration == 0) revert InvalidExpiry();

        requestId = nextRequestId++;

        uint256 expiresAt = block.timestamp + expiryDuration;

        requests[requestId] = PaymentRequest({
            id: requestId,
            requester: msg.sender,
            payer: payer,
            amount: amount,
            reason: reason,
            expiresAt: expiresAt,
            status: RequestStatus.Pending,
            createdAt: block.timestamp
        });

        emit RequestCreated(
            requestId,
            msg.sender,
            payer,
            amount,
            reason,
            expiresAt
        );
    }

    /// @notice Fulfill (pay) a payment request
    /// @param requestId The ID of the request to fulfill
    function fulfillRequest(uint256 requestId) external nonReentrant {
        PaymentRequest storage req = requests[requestId];

        if (req.requester == address(0)) revert RequestNotFound();
        if (req.status != RequestStatus.Pending) revert RequestNotPending();
        if (msg.sender != req.payer) revert NotRequestPayer();
        if (block.timestamp > req.expiresAt) {
            req.status = RequestStatus.Expired;
            revert RequestExpired();
        }

        req.status = RequestStatus.Fulfilled;

        usdc.safeTransferFrom(msg.sender, req.requester, req.amount);

        emit RequestFulfilled(requestId, msg.sender, req.requester, req.amount);
    }

    /// @notice Cancel a payment request (only the requester can cancel)
    /// @param requestId The ID of the request to cancel
    function cancelRequest(uint256 requestId) external {
        PaymentRequest storage req = requests[requestId];

        if (req.requester == address(0)) revert RequestNotFound();
        if (req.status != RequestStatus.Pending) revert RequestNotPending();
        if (msg.sender != req.requester) revert NotRequestRequester();

        req.status = RequestStatus.Cancelled;

        emit RequestCancelled(requestId);
    }

    // -------------------------------------------------------------------------
    // Views
    // -------------------------------------------------------------------------

    /// @notice Get a payment request by ID
    /// @param requestId The ID of the request
    /// @return The PaymentRequest struct
    function getRequest(
        uint256 requestId
    ) external view returns (PaymentRequest memory) {
        return requests[requestId];
    }

    /// @notice Check if a request is expired
    /// @param requestId The ID of the request
    /// @return True if the request has expired
    function isExpired(uint256 requestId) external view returns (bool) {
        PaymentRequest storage req = requests[requestId];
        return
            req.status == RequestStatus.Pending &&
            block.timestamp > req.expiresAt;
    }

    // -------------------------------------------------------------------------
    // Admin
    // -------------------------------------------------------------------------

    /// @notice Update the default expiry duration
    /// @param newExpiry New default expiry in seconds
    function setDefaultExpiry(uint256 newExpiry) external onlyOwner {
        if (newExpiry == 0) revert InvalidExpiry();
        defaultExpiry = newExpiry;
        emit DefaultExpiryUpdated(newExpiry);
    }
}
