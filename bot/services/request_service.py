"""Request service - on-chain payment request management."""

import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

from web3 import Web3
from eth_account import Account

from bot.config import (
    ARC_RPC_URL,
    USDC_CONTRACT_ADDRESS,
    ESCROW_CONTRACT_ADDRESS,
    ERC20_ABI,
    ESCROW_ABI,
    USDC_DECIMALS,
)
from bot.db.database import Database
from bot.models.payment import Payment, PaymentRequest, PaymentType, PaymentStatus
from bot.utils.encryption import decrypt_private_key

logger = logging.getLogger(__name__)


class RequestService:
    """Manages payment requests via the ArcPayEscrow contract."""

    def __init__(self, db: Database):
        self.db = db
        self.w3 = Web3(Web3.HTTPProvider(ARC_RPC_URL))

    def _get_escrow_contract(self):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(ESCROW_CONTRACT_ADDRESS),
            abi=ESCROW_ABI,
        )

    def _get_usdc_contract(self):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_CONTRACT_ADDRESS),
            abi=ERC20_ABI,
        )

    async def create_request(
        self,
        requester_id: int,
        payer_id: int,
        requester_address: str,
        payer_address: str,
        amount: float,
        reason: str,
        encrypted_private_key: str,
    ) -> Optional[PaymentRequest]:
        """Create a payment request on-chain and record in DB."""
        try:
            private_key = decrypt_private_key(encrypted_private_key)
            escrow = self._get_escrow_contract()
            amount_units = int(amount * (10**USDC_DECIMALS))

            from_checksum = Web3.to_checksum_address(requester_address)
            payer_checksum = Web3.to_checksum_address(payer_address)

            nonce = self.w3.eth.get_transaction_count(from_checksum)

            tx = escrow.functions.createRequest(
                payer_checksum, amount_units, reason
            ).build_transaction(
                {
                    "from": from_checksum,
                    "nonce": nonce,
                    "gas": 200_000,
                    "gasPrice": self.w3.eth.gas_price,
                }
            )

            signed = Account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            # Parse the requestId from events (simplified: use nextRequestId - 1)
            chain_request_id = escrow.functions.getRequest(0).call()[0]

            # Store in DB
            expires_at = (
                datetime.now(timezone.utc) + timedelta(days=7)
            ).isoformat()

            req = PaymentRequest(
                id=None,
                requester_id=requester_id,
                payer_id=payer_id,
                amount=amount,
                reason=reason,
                chain_request_id=chain_request_id,
                status=PaymentStatus.PENDING,
                expires_at=expires_at,
            )
            return await self.db.create_payment_request(req)

        except Exception as e:
            logger.error("Failed to create request: %s", str(e))
            # Fall back to off-chain request
            return await self.create_offchain_request(
                requester_id, payer_id, amount, reason
            )

    async def create_offchain_request(
        self,
        requester_id: int,
        payer_id: int,
        amount: float,
        reason: str,
    ) -> PaymentRequest:
        """Create an off-chain payment request (DB only)."""
        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=7)
        ).isoformat()

        req = PaymentRequest(
            id=None,
            requester_id=requester_id,
            payer_id=payer_id,
            amount=amount,
            reason=reason,
            chain_request_id=None,
            status=PaymentStatus.PENDING,
            expires_at=expires_at,
        )
        return await self.db.create_payment_request(req)

    async def fulfill_request(
        self,
        request_id: int,
        payer_address: str,
        requester_address: str,
        encrypted_private_key: str,
        amount: float,
        payer_id: int,
        requester_id: int,
    ) -> Optional[str]:
        """Fulfill a payment request by sending USDC."""
        try:
            private_key = decrypt_private_key(encrypted_private_key)
            usdc = self._get_usdc_contract()
            amount_units = int(amount * (10**USDC_DECIMALS))

            from_checksum = Web3.to_checksum_address(payer_address)
            to_checksum = Web3.to_checksum_address(requester_address)

            nonce = self.w3.eth.get_transaction_count(from_checksum)

            tx = usdc.functions.transfer(
                to_checksum, amount_units
            ).build_transaction(
                {
                    "from": from_checksum,
                    "nonce": nonce,
                    "gas": 100_000,
                    "gasPrice": self.w3.eth.gas_price,
                }
            )

            signed = Account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            # Update request status
            await self.db.update_request_status(
                request_id, PaymentStatus.COMPLETED
            )

            # Record payment
            payment = Payment(
                id=None,
                from_user_id=payer_id,
                to_user_id=requester_id,
                amount=amount,
                memo=f"Request #{request_id} fulfilled",
                tx_hash=tx_hash_hex,
                payment_type=PaymentType.REQUEST,
                status=PaymentStatus.COMPLETED,
            )
            await self.db.create_payment(payment)

            return tx_hash_hex

        except Exception as e:
            logger.error("Failed to fulfill request: %s", str(e))
            return None
