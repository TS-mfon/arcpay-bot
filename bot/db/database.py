"""SQLite database layer for ArcPay."""

import aiosqlite
from typing import Optional, List

from bot.config import DATABASE_PATH
from bot.models.user import User
from bot.models.payment import Payment, PaymentRequest, PaymentType, PaymentStatus


class Database:
    """Async SQLite database for user and payment data."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Create tables if they don't exist."""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row

        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                wallet_address TEXT NOT NULL,
                encrypted_private_key TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER,
                amount REAL NOT NULL,
                memo TEXT,
                tx_hash TEXT,
                payment_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_user_id) REFERENCES users(telegram_id),
                FOREIGN KEY (to_user_id) REFERENCES users(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS payment_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requester_id INTEGER NOT NULL,
                payer_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                reason TEXT,
                chain_request_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (requester_id) REFERENCES users(telegram_id),
                FOREIGN KEY (payer_id) REFERENCES users(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS payment_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                reason TEXT,
                link_code TEXT UNIQUE NOT NULL,
                claimer_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                tx_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES users(telegram_id),
                FOREIGN KEY (claimer_id) REFERENCES users(telegram_id)
            );
            """
        )
        await self._db.commit()

    async def close(self):
        """Close database connection."""
        if self._db:
            await self._db.close()

    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------

    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Get a user by Telegram ID."""
        async with self._db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return User(
                    telegram_id=row["telegram_id"],
                    username=row["username"],
                    wallet_address=row["wallet_address"],
                    encrypted_private_key=row["encrypted_private_key"],
                    created_at=row["created_at"],
                )
        return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by Telegram username."""
        clean = username.lstrip("@").lower()
        async with self._db.execute(
            "SELECT * FROM users WHERE LOWER(username) = ?", (clean,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return User(
                    telegram_id=row["telegram_id"],
                    username=row["username"],
                    wallet_address=row["wallet_address"],
                    encrypted_private_key=row["encrypted_private_key"],
                    created_at=row["created_at"],
                )
        return None

    async def create_user(self, user: User) -> User:
        """Insert a new user."""
        await self._db.execute(
            """INSERT INTO users (telegram_id, username, wallet_address, encrypted_private_key)
               VALUES (?, ?, ?, ?)""",
            (
                user.telegram_id,
                user.username,
                user.wallet_address,
                user.encrypted_private_key,
            ),
        )
        await self._db.commit()
        return user

    async def update_username(self, telegram_id: int, username: str):
        """Update a user's username."""
        await self._db.execute(
            "UPDATE users SET username = ? WHERE telegram_id = ?",
            (username, telegram_id),
        )
        await self._db.commit()

    # -------------------------------------------------------------------------
    # Payments
    # -------------------------------------------------------------------------

    async def create_payment(self, payment: Payment) -> Payment:
        """Record a payment."""
        async with self._db.execute(
            """INSERT INTO payments
               (from_user_id, to_user_id, amount, memo, tx_hash, payment_type, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                payment.from_user_id,
                payment.to_user_id,
                payment.amount,
                payment.memo,
                payment.tx_hash,
                payment.payment_type.value,
                payment.status.value,
            ),
        ) as cursor:
            payment.id = cursor.lastrowid
        await self._db.commit()
        return payment

    async def get_payment_by_tx(self, tx_hash: str) -> Optional[Payment]:
        """Get a payment by transaction hash."""
        async with self._db.execute(
            "SELECT * FROM payments WHERE tx_hash = ?", (tx_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_payment(row)
        return None

    async def update_payment_status_by_tx(self, tx_hash: str, status: str) -> None:
        """Update payment status by tx hash (used by receipt watcher)."""
        await self._db.execute(
            "UPDATE payments SET status = ? WHERE tx_hash = ?",
            (status, tx_hash),
        )
        await self._db.commit()

    async def get_user_payments(
        self, telegram_id: int, limit: int = 20
    ) -> List[Payment]:
        """Get recent payments for a user."""
        async with self._db.execute(
            """SELECT * FROM payments
               WHERE from_user_id = ? OR to_user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (telegram_id, telegram_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_payment(r) for r in rows]

    # -------------------------------------------------------------------------
    # Payment Requests
    # -------------------------------------------------------------------------

    async def create_payment_request(self, req: PaymentRequest) -> PaymentRequest:
        """Create a payment request."""
        async with self._db.execute(
            """INSERT INTO payment_requests
               (requester_id, payer_id, amount, reason, chain_request_id, status, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                req.requester_id,
                req.payer_id,
                req.amount,
                req.reason,
                req.chain_request_id,
                req.status.value,
                req.expires_at,
            ),
        ) as cursor:
            req.id = cursor.lastrowid
        await self._db.commit()
        return req

    async def get_payment_request(self, request_id: int) -> Optional[PaymentRequest]:
        """Get a payment request by ID."""
        async with self._db.execute(
            "SELECT * FROM payment_requests WHERE id = ?", (request_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_request(row)
        return None

    async def get_pending_requests_for_user(
        self, telegram_id: int
    ) -> List[PaymentRequest]:
        """Get pending requests where user is the payer."""
        async with self._db.execute(
            """SELECT * FROM payment_requests
               WHERE payer_id = ? AND status = 'pending'
               ORDER BY created_at DESC""",
            (telegram_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_request(r) for r in rows]

    async def update_request_status(self, request_id: int, status: PaymentStatus):
        """Update a payment request's status."""
        await self._db.execute(
            "UPDATE payment_requests SET status = ? WHERE id = ?",
            (status.value, request_id),
        )
        await self._db.commit()

    # -------------------------------------------------------------------------
    # Payment Links
    # -------------------------------------------------------------------------

    async def create_payment_link(
        self, creator_id: int, amount: float, reason: str, link_code: str
    ):
        """Create a payment link."""
        await self._db.execute(
            """INSERT INTO payment_links (creator_id, amount, reason, link_code)
               VALUES (?, ?, ?, ?)""",
            (creator_id, amount, reason, link_code),
        )
        await self._db.commit()

    async def get_payment_link(self, link_code: str) -> Optional[dict]:
        """Get a payment link by code."""
        async with self._db.execute(
            "SELECT * FROM payment_links WHERE link_code = ?", (link_code,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
        return None

    async def claim_payment_link(
        self, link_code: str, claimer_id: int, tx_hash: str
    ):
        """Mark a payment link as claimed."""
        await self._db.execute(
            """UPDATE payment_links
               SET claimer_id = ?, status = 'completed', tx_hash = ?
               WHERE link_code = ?""",
            (claimer_id, tx_hash, link_code),
        )
        await self._db.commit()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _row_to_payment(row) -> Payment:
        return Payment(
            id=row["id"],
            from_user_id=row["from_user_id"],
            to_user_id=row["to_user_id"],
            amount=row["amount"],
            memo=row["memo"],
            tx_hash=row["tx_hash"],
            payment_type=PaymentType(row["payment_type"]),
            status=PaymentStatus(row["status"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_request(row) -> PaymentRequest:
        return PaymentRequest(
            id=row["id"],
            requester_id=row["requester_id"],
            payer_id=row["payer_id"],
            amount=row["amount"],
            reason=row["reason"],
            chain_request_id=row["chain_request_id"],
            status=PaymentStatus(row["status"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )
