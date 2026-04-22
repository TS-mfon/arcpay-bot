"""Payment service - on-chain USDC transfers on Arc Network.

On Arc, USDC is the NATIVE gas token (like ETH on Ethereum).
So we use native value transfers, not ERC20 calls.
"""

import logging
from typing import Optional

from web3 import Web3
from eth_account import Account

from bot.config import ARC_RPC_URL
from bot.db.database import Database
from bot.models.payment import Payment, PaymentType, PaymentStatus
from bot.utils.encryption import decrypt_private_key

logger = logging.getLogger(__name__)


class PaymentService:
    """Handles on-chain USDC payments on Arc Network.

    Since USDC is Arc's native token, all transfers are simple
    value transfers (like sending ETH on Ethereum).
    """

    def __init__(self, db: Database):
        self.db = db
        self.w3 = Web3(Web3.HTTPProvider(ARC_RPC_URL))

    def _to_wei(self, amount: float) -> int:
        """Convert human-readable USDC amount to wei (18 decimals on Arc)."""
        return self.w3.to_wei(amount, "ether")

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
        """Send USDC (native token) from one user to another.

        On Arc, this is a simple native value transfer.
        Returns the transaction hash or None on failure.
        """
        try:
            private_key = decrypt_private_key(encrypted_private_key)
            amount_wei = self._to_wei(amount)

            from_checksum = Web3.to_checksum_address(from_address)
            to_checksum = Web3.to_checksum_address(to_address)

            nonce = self.w3.eth.get_transaction_count(from_checksum)
            gas_price = self.w3.eth.gas_price

            tx = {
                "from": from_checksum,
                "to": to_checksum,
                "value": amount_wei,
                "nonce": nonce,
                "gas": 21_000,  # Standard transfer gas
                "gasPrice": gas_price,
                "chainId": self.w3.eth.chain_id,
            }

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
                "Payment sent: %s -> %s, amount=%s USDC, tx=%s",
                from_address, to_address, amount, tx_hash_hex,
            )

            # Send notification to recipient if they're a bot user
            if to_user_id and to_user_id > 0:
                try:
                    bot = self.w3  # placeholder - notification handled in handler
                    logger.info("Recipient %s should be notified", to_user_id)
                except Exception:
                    pass

            return tx_hash_hex

        except Exception as e:
            logger.error("Payment failed: %s", str(e))
            return None

    async def batch_send(
        self,
        from_user_id: int,
        from_address: str,
        recipients: list[tuple[int, str]],
        amounts: list[float],
        encrypted_private_key: str,
        memo: str = "",
    ) -> list[Optional[str]]:
        """Send USDC to multiple recipients as individual native transfers.

        Returns list of tx hashes (one per recipient).
        """
        results = []
        for i, (user_id, addr) in enumerate(recipients):
            tx_hash = await self.send_usdc(
                from_user_id=from_user_id,
                to_user_id=user_id,
                from_address=from_address,
                to_address=addr,
                amount=amounts[i],
                encrypted_private_key=encrypted_private_key,
                memo=memo,
                payment_type=PaymentType.SPLIT,
            )
            results.append(tx_hash)
        return results
