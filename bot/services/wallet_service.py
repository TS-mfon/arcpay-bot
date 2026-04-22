"""Wallet service - create and manage embedded wallets."""

from eth_account import Account

from bot.db.database import Database
from bot.models.user import User
from bot.utils.encryption import encrypt_private_key, decrypt_private_key
from bot.config import ARC_RPC_URL, USDC_CONTRACT_ADDRESS, ERC20_ABI

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
            # Update username if changed
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
        """Get USDC balance for an address."""
        if not USDC_CONTRACT_ADDRESS:
            return 0.0

        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(USDC_CONTRACT_ADDRESS),
                abi=ERC20_ABI,
            )
            balance_raw = contract.functions.balanceOf(
                Web3.to_checksum_address(address)
            ).call()
            return balance_raw / 1e6  # USDC has 6 decimals
        except Exception:
            return 0.0

    async def get_eth_balance(self, address: str) -> float:
        """Get native ETH/ARC balance for gas."""
        try:
            balance_wei = self.w3.eth.get_balance(
                Web3.to_checksum_address(address)
            )
            return self.w3.from_wei(balance_wei, "ether")
        except Exception:
            return 0.0
