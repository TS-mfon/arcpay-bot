"""User model for ArcPay."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """Represents an ArcPay user with an embedded wallet."""

    telegram_id: int
    username: Optional[str]
    wallet_address: str
    encrypted_private_key: str
    created_at: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Return a display-friendly name."""
        if self.username:
            return f"@{self.username}"
        return f"User#{self.telegram_id}"
