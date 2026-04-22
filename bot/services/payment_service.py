"""Payment service - on-chain USDC transfers."""

import logging
from typing import Optional

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
from bot.models.payment import Payment, PaymentType, PaymentStatus
from bot.utils.encryption import decrypt_private_key

logger = logging.getLogger(__name__)


class PaymentService:
    """Handles on-chain USDC payments."""

    def __init__(self, db: Database):
        self.db = db
        self.w3 = Web3(Web3.HTTPProvider(ARC_RPC_URL))

    def _get_usdc_contract(self):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_CONTRACT_ADDRESS),
            abi=ERC20_ABI,
        )

    def _get_escrow_contract(self):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(ESCROW_CONTRACT_ADDRESS),
            abi=ESCROW_ABI,
        )

    def _to_usdc_units(self, amount: float) -> int:
        """Convert human-readable amount to USDC units (6 decimals)."""
        return int(amount * (10**USDC_DECIMALS))

    async def send_usdc(
        self,
        from_user_id: int,
        to_user_id: int,
        from_address: str,
        to_address: str,
        amount: float,
        encrypted_private_key: str,
        memo: Optional[str] = None,
        payment_type: PaymentType = PaymentType.SEND,
    ) -> Optional[str]:
        """Send USDC from one user to another via direct transfer.

        Returns the transaction hash or None on failure.
        """
        try:
            private_key = decrypt_private_key(encrypted_private_key)
            usdc = self._get_usdc_contract()
            amount_units = self._to_usdc_units(amount)

            from_checksum = Web3.to_checksum_address(from_address)
            to_checksum = Web3.to_checksum_address(to_address)

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

            # Record in database
            payment = Payment(
                id=None,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                amount=amount,
                memo=memo,
                tx_hash=tx_hash_hex,
                payment_type=payment_type,
                status=PaymentStatus.COMPLETED,
            )
            await self.db.create_payment(payment)

            logger.info(
                "Payment sent: %s -> %s, amount=%s, tx=%s",
                from_address,
                to_address,
                amount,
                tx_hash_hex,
            )
            return tx_hash_hex

        except Exception as e:
            logger.error("Payment failed: %s", str(e))
            return None

    async def send_via_escrow(
        self,
        from_user_id: int,
        to_user_id: int,
        from_address: str,
        to_address: str,
        amount: float,
        encrypted_private_key: str,
        memo: str = "",
    ) -> Optional[str]:
        """Send USDC via the ArcPayEscrow contract."""
        try:
            private_key = decrypt_private_key(encrypted_private_key)
            escrow = self._get_escrow_contract()
            usdc = self._get_usdc_contract()
            amount_units = self._to_usdc_units(amount)

            from_checksum = Web3.to_checksum_address(from_address)
            to_checksum = Web3.to_checksum_address(to_address)
            escrow_address = Web3.to_checksum_address(ESCROW_CONTRACT_ADDRESS)

            nonce = self.w3.eth.get_transaction_count(from_checksum)

            # Approve escrow to spend USDC
            approve_tx = usdc.functions.approve(
                escrow_address, amount_units
            ).build_transaction(
                {
                    "from": from_checksum,
                    "nonce": nonce,
                    "gas": 60_000,
                    "gasPrice": self.w3.eth.gas_price,
                }
            )
            signed_approve = Account.sign_transaction(approve_tx, private_key)
            self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            nonce += 1

            # Send via escrow
            send_tx = escrow.functions.sendPayment(
                to_checksum, amount_units, memo
            ).build_transaction(
                {
                    "from": from_checksum,
                    "nonce": nonce,
                    "gas": 150_000,
                    "gasPrice": self.w3.eth.gas_price,
                }
            )
            signed_send = Account.sign_transaction(send_tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_send.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            # Record in database
            payment = Payment(
                id=None,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                amount=amount,
                memo=memo,
                tx_hash=tx_hash_hex,
                payment_type=PaymentType.SEND,
                status=PaymentStatus.COMPLETED,
            )
            await self.db.create_payment(payment)

            return tx_hash_hex

        except Exception as e:
            logger.error("Escrow payment failed: %s", str(e))
            return None

    async def batch_send(
        self,
        from_user_id: int,
        from_address: str,
        recipients: list[tuple[int, str]],
        amounts: list[float],
        encrypted_private_key: str,
        memo: str = "",
    ) -> Optional[str]:
        """Send USDC to multiple recipients via the escrow batch function.

        recipients: list of (telegram_id, wallet_address) tuples
        """
        try:
            private_key = decrypt_private_key(encrypted_private_key)
            escrow = self._get_escrow_contract()
            usdc = self._get_usdc_contract()

            from_checksum = Web3.to_checksum_address(from_address)
            escrow_address = Web3.to_checksum_address(ESCROW_CONTRACT_ADDRESS)

            to_addresses = [
                Web3.to_checksum_address(addr) for _, addr in recipients
            ]
            amount_units = [self._to_usdc_units(a) for a in amounts]
            total_units = sum(amount_units)

            nonce = self.w3.eth.get_transaction_count(from_checksum)

            # Approve total
            approve_tx = usdc.functions.approve(
                escrow_address, total_units
            ).build_transaction(
                {
                    "from": from_checksum,
                    "nonce": nonce,
                    "gas": 60_000,
                    "gasPrice": self.w3.eth.gas_price,
                }
            )
            signed_approve = Account.sign_transaction(approve_tx, private_key)
            self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            nonce += 1

            # Batch send
            batch_tx = escrow.functions.batchSendPayment(
                to_addresses, amount_units, memo
            ).build_transaction(
                {
                    "from": from_checksum,
                    "nonce": nonce,
                    "gas": 50_000 + 100_000 * len(recipients),
                    "gasPrice": self.w3.eth.gas_price,
                }
            )
            signed_batch = Account.sign_transaction(batch_tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_batch.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            # Record individual payments
            for i, (user_id, _) in enumerate(recipients):
                payment = Payment(
                    id=None,
                    from_user_id=from_user_id,
                    to_user_id=user_id,
                    amount=amounts[i],
                    memo=memo,
                    tx_hash=tx_hash_hex,
                    payment_type=PaymentType.SPLIT,
                    status=PaymentStatus.COMPLETED,
                )
                await self.db.create_payment(payment)

            return tx_hash_hex

        except Exception as e:
            logger.error("Batch payment failed: %s", str(e))
            return None
