"""Payment service - on-chain native USDC transfers on Arc Network.

On Arc, USDC is the NATIVE gas token (chain id 5042002).
So all transfers are simple native value transfers like sending ETH.
"""

import asyncio
import logging
from typing import Optional

from web3 import Web3
from eth_account import Account

from bot.config import ARC_RPC_URL, ARC_CHAIN_ID
from bot.db.database import Database
from bot.models.payment import Payment, PaymentType, PaymentStatus
from bot.utils.encryption import decrypt_private_key

logger = logging.getLogger(__name__)

GAS_LIMIT_NATIVE = 21_000
RECEIPT_POLL_ATTEMPTS = 30
RECEIPT_POLL_INTERVAL = 2.0  # seconds


class PaymentService:
    """Handles on-chain USDC payments on Arc Network."""

    def __init__(self, db: Database):
        self.db = db
        self.w3 = Web3(Web3.HTTPProvider(ARC_RPC_URL, request_kwargs={"timeout": 30}))

    def _to_wei(self, amount: float) -> int:
        """Convert human-readable USDC to 18-decimal wei (Arc native)."""
        return self.w3.to_wei(amount, "ether")

    async def _wait_receipt(self, tx_hash: str) -> dict | None:
        """Poll for transaction receipt with timeout."""
        for _ in range(RECEIPT_POLL_ATTEMPTS):
            try:
                receipt = await asyncio.to_thread(
                    self.w3.eth.get_transaction_receipt, tx_hash
                )
                if receipt is not None:
                    return dict(receipt)
            except Exception:
                pass
            await asyncio.sleep(RECEIPT_POLL_INTERVAL)
        return None

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
        """Send USDC (native) between addresses on Arc.

        Returns tx hash on success or None on failure.
        Writes to DB with PENDING status immediately, updates to
        COMPLETED or FAILED after receipt polling.
        """
        try:
            private_key = decrypt_private_key(encrypted_private_key)
            amount_wei = self._to_wei(amount)

            from_checksum = Web3.to_checksum_address(from_address)
            to_checksum = Web3.to_checksum_address(to_address)

            # Build and sign off the event loop
            def _build_and_sign():
                nonce = self.w3.eth.get_transaction_count(from_checksum)
                gas_price = int(self.w3.eth.gas_price * 1.1)  # 10% buffer
                tx = {
                    "from": from_checksum,
                    "to": to_checksum,
                    "value": amount_wei,
                    "nonce": nonce,
                    "gas": GAS_LIMIT_NATIVE,
                    "gasPrice": gas_price,
                    "chainId": ARC_CHAIN_ID,
                }
                signed = Account.sign_transaction(tx, private_key)
                return signed.raw_transaction

            raw_tx = await asyncio.to_thread(_build_and_sign)
            tx_hash_bytes = await asyncio.to_thread(self.w3.eth.send_raw_transaction, raw_tx)
            tx_hash_hex = tx_hash_bytes.hex()
            if not tx_hash_hex.startswith("0x"):
                tx_hash_hex = "0x" + tx_hash_hex

            # Record as pending
            payment = Payment(
                id=None,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                amount=amount,
                memo=memo,
                tx_hash=tx_hash_hex,
                payment_type=payment_type,
                status=PaymentStatus.PENDING,
            )
            try:
                await self.db.create_payment(payment)
            except Exception:
                logger.exception("DB insert failed (non-fatal)")

            # Fire-and-forget receipt watcher (updates DB)
            asyncio.create_task(self._watch_receipt(tx_hash_hex))

            logger.info(
                "TX sent: %s -> %s  amount=%s  hash=%s",
                from_address, to_address, amount, tx_hash_hex,
            )
            return tx_hash_hex

        except Exception as e:
            logger.exception("send_usdc failed: %s", e)
            return None

    async def _watch_receipt(self, tx_hash: str) -> None:
        """Update DB once the tx confirms or fails."""
        receipt = await self._wait_receipt(tx_hash)
        if receipt is None:
            logger.warning("Receipt timeout for %s", tx_hash)
            return
        status = PaymentStatus.COMPLETED if receipt.get("status") == 1 else PaymentStatus.FAILED
        try:
            await self.db.update_payment_status_by_tx(tx_hash, status.value)
        except Exception:
            logger.exception("DB update failed")

    async def batch_send(
        self,
        from_user_id: int,
        from_address: str,
        recipients: list[tuple[int, str]],
        amounts: list[float],
        encrypted_private_key: str,
        memo: str = "",
    ) -> list[Optional[str]]:
        """Send to multiple recipients as sequential native transfers."""
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
            # Small delay between transfers to avoid nonce collision
            await asyncio.sleep(0.5)
        return results
