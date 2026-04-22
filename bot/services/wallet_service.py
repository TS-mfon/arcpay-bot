"""Wallet service - create and manage embedded wallets."""

from eth_account import Account

from bot.db.database import Database
from bot.models.user import User
from bot.utils.encryption import encrypt_private_key, decrypt_private_key
from bot.config import ARC_RPC_URL

from web3 import Web3


def get_web3() -> Web3:
    """Get a Web3 instance connected to Arc Network."""
    return Web3(Web3.HTTPProvider(ARC_RPC_URL))


class WalletService:
    """Manages embedded wallets for Telegram users."""

    def __init__(self, db: Database):
        self.db = db
        self.w3 = get_web3()

    async def get_or_create_user(
        self, telegram_id: int, username: str | None = None
    ) -> User:
        """Get existing user or create a new embedded wallet."""
        user = await self.db.get_user(telegram_id)

        if user:
            if username and user.username != username:
                await self.db.update_username(telegram_id, username)
                user.username = username
            return user

        # Generate a new Ethereum account
        account = Account.create()
        encrypted_key = encrypt_private_key(account.key.hex())

        user = User(
            telegram_id=telegram_id,
            username=username,
            wallet_address=account.address,
            encrypted_private_key=encrypted_key,
        )

        await self.db.create_user(user)
        return user

    def get_private_key(self, user: User) -> str:
        """Decrypt and return the user's private key."""
        return decrypt_private_key(user.encrypted_private_key)

    async def get_usdc_balance(self, address: str) -> float:
        """Get USDC balance for an address.

        On Arc Network, USDC is the NATIVE gas token.
        So we use eth_getBalance, not an ERC20 call.
        The balance is returned in 18 decimals (like ETH).
        """
        try:
            balance_wei = self.w3.eth.get_balance(
                Web3.to_checksum_address(address)
            )
            # Arc native token (USDC) uses 18 decimals
            return float(self.w3.from_wei(balance_wei, "ether"))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Balance check failed: {e}")
            return 0.0

    async def resolve_user_by_username(self, username: str) -> User | None:
        """Resolve a Telegram @username to a registered user."""
        username = username.lstrip("@")
        return await self.db.get_user_by_username(username)
