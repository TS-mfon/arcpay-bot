"""/send @user <amount> [memo] command handler."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.wallet_service import WalletService
from bot.services.payment_service import PaymentService
from bot.services.user_resolver import UserResolver
from bot.utils.formatting import format_usdc, payment_confirmation


async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /send @user <amount> [memo]."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /send @username <amount> [memo]\n"
            "Example: /send @alice 25.00 lunch money"
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

    memo = " ".join(context.args[2:]) if len(context.args) > 2 else None

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

    await update.message.reply_text(
        f"Sending {format_usdc(amount)} to {recipient.display_name}..."
    )

    tx_hash = await payment_svc.send_usdc(
        from_user_id=sender.telegram_id,
        to_user_id=recipient.telegram_id,
        from_address=sender.wallet_address,
        to_address=recipient.wallet_address,
        amount=amount,
        encrypted_private_key=sender.encrypted_private_key,
        memo=memo,
    )

    if tx_hash:
        msg = payment_confirmation(
            sender=sender.display_name,
            recipient=recipient.display_name,
            amount=amount,
            memo=memo,
            tx_hash=tx_hash,
        )
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text(
            "Payment failed. Please check your balance and try again."
        )
