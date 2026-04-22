"""/history command handler."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.wallet_service import WalletService
from bot.utils.formatting import format_usdc, format_tx_hash


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /history - show recent transactions."""
    db = context.application.bot_data["db"]
    wallet_svc = WalletService(db)

    user = await wallet_svc.get_or_create_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )

    payments = await db.get_user_payments(user.telegram_id, limit=10)

    if not payments:
        await update.message.reply_text(
            "No transactions yet. Send your first payment with /send!"
        )
        return

    lines = ["Transaction History", "=" * 25, ""]

    for p in payments:
        direction = "SENT" if p.from_user_id == user.telegram_id else "RECEIVED"
        icon = "[-]" if direction == "SENT" else "[+]"

        # Resolve other party
        other_id = (
            p.to_user_id if p.from_user_id == user.telegram_id else p.from_user_id
        )
        other_user = await db.get_user(other_id) if other_id else None
        other_name = other_user.display_name if other_user else "External"

        line = f"{icon} {format_usdc(p.amount)} {direction}"
        line += f" {'to' if direction == 'SENT' else 'from'} {other_name}"

        if p.memo:
            line += f" | {p.memo}"
        if p.tx_hash:
            line += f"\n    Tx: {format_tx_hash(p.tx_hash)}"
        if p.created_at:
            line += f"\n    {p.created_at}"

        lines.append(line)
        lines.append("")

    await update.message.reply_text("\n".join(lines))
