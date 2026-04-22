"""User resolver - map @username to wallet address."""

from typing import Optional

from bot.db.database import Database
from bot.models.user import User


class UserResolver:
    """Resolves Telegram usernames to ArcPay users and wallet addresses."""

    def __init__(self, db: Database):
        self.db = db

    async def resolve_username(self, username: str) -> Optional[User]:
        """Resolve a @username to a User.

        Args:
            username: Telegram username, with or without '@' prefix.

        Returns:
            The User if found, else None.
        """
        clean = username.lstrip("@")
        return await self.db.get_user_by_username(clean)

    async def resolve_user_id(self, telegram_id: int) -> Optional[User]:
        """Resolve a Telegram user ID to a User."""
        return await self.db.get_user(telegram_id)

    async def resolve_to_address(self, username: str) -> Optional[str]:
        """Resolve a @username directly to a wallet address."""
        user = await self.resolve_username(username)
        if user:
            return user.wallet_address
        return None

    async def ensure_user_exists(
        self, telegram_id: int, username: Optional[str] = None
    ) -> bool:
        """Check if a user exists in the system."""
        user = await self.db.get_user(telegram_id)
        return user is not None
