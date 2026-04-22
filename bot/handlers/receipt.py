"""/receipt command handler - generate receipt images."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.wallet_service import WalletService
from bot.services.receipt_generator import ReceiptGenerator


async def receipt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /receipt <tx_hash> - generate a receipt image."""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /receipt <tx_hash>\n"
            "Example: /receipt 0xabc123..."
        )
        return

    tx_hash = context.args[0]

    db = context.application.bot_data["db"]
    wallet_svc = WalletService(db)

    # Ensure user is registered
    user = await wallet_svc.get_or_create_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )

    # Look up payment
    payment = await db.get_payment_by_tx(tx_hash)
    if not payment:
        await update.message.reply_text(
            f"No payment found for transaction: {tx_hash}\n"
            f"Only payments made through ArcPay are tracked."
        )
        return

    # Resolve sender and recipient
    sender = await db.get_user(payment.from_user_id)
    recipient = await db.get_user(payment.to_user_id) if payment.to_user_id else None

    from_name = sender.display_name if sender else f"User#{payment.from_user_id}"
    to_name = (
        recipient.display_name
        if recipient
        else f"User#{payment.to_user_id}"
    )

    # Generate receipt image
    generator = ReceiptGenerator()
    image_buffer = generator.generate_receipt(
        from_name=from_name,
        to_name=to_name,
        amount=payment.amount,
        memo=payment.memo,
        tx_hash=payment.tx_hash,
        timestamp=payment.created_at,
    )

    await update.message.reply_photo(
        photo=image_buffer,
        caption=f"Receipt for {payment.amount_display}",
    )
