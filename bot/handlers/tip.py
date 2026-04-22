"""/tip @user <amount> command handler."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.wallet_service import WalletService
from bot.services.payment_service import PaymentService
from bot.services.user_resolver import UserResolver
from bot.models.payment import PaymentType
from bot.utils.formatting import format_usdc


async def tip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tip @user <amount>."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /tip @username <amount>\n" "Example: /tip @alice 5.00"
        )
        return

    recipient_username = context.args[0]
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    if amount <= 0:
        await update.message.reply_text("Amount must be greater than zero.")
        return

    db = context.application.bot_data["db"]
    wallet_svc = WalletService(db)
    payment_svc = PaymentService(db)
    resolver = UserResolver(db)

    # Get sender
    sender = await wallet_svc.get_or_create_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )

    # Resolve recipient
    recipient = await resolver.resolve_username(recipient_username)
    if not recipient:
        await update.message.reply_text(
            f"User {recipient_username} not found. "
            f"They need to /start the bot first."
        )
        return

    # Check balance
    balance = await wallet_svc.get_usdc_balance(sender.wallet_address)
    if balance < amount:
        await update.message.reply_text(
            f"Insufficient balance. You have {format_usdc(balance)}."
        )
        return

    tx_hash = await payment_svc.send_usdc(
        from_user_id=sender.telegram_id,
        to_user_id=recipient.telegram_id,
        from_address=sender.wallet_address,
        to_address=recipient.wallet_address,
        amount=amount,
        encrypted_private_key=sender.encrypted_private_key,
        memo="Tip",
        payment_type=PaymentType.TIP,
    )

    if tx_hash:
        await update.message.reply_text(
            f"Tip Sent!\n"
            f"{sender.display_name} tipped {recipient.display_name} "
            f"{format_usdc(amount)}\n"
            f"Tx: {tx_hash}"
        )
    else:
        await update.message.reply_text(
            "Tip failed. Please check your balance and try again."
        )
