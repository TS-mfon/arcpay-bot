"""Payment and request models for ArcPay."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PaymentType(str, Enum):
    SEND = "send"
    REQUEST = "request"
    TIP = "tip"
    SPLIT = "split"
    LINK = "link"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class Payment:
    """Represents a payment transaction."""

    id: Optional[int]
    from_user_id: int
    to_user_id: Optional[int]
    amount: float
    memo: Optional[str]
    tx_hash: Optional[str]
    payment_type: PaymentType
    status: PaymentStatus
    created_at: Optional[str] = None

    @property
    def amount_display(self) -> str:
        """Format amount for display."""
        return f"${self.amount:.2f}"


@dataclass
class PaymentRequest:
    """Represents a payment request."""

    id: Optional[int]
    requester_id: int
    payer_id: int
    amount: float
    reason: str
    chain_request_id: Optional[int]
    status: PaymentStatus
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
