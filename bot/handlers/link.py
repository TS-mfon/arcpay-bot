"""/link command handler - create payment links."""

import secrets

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.wallet_service import WalletService
from bot.utils.formatting import format_usdc


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /link <amount> <reason> - create a payment link.

    Generates a unique link code that another user can claim.
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /link <amount> <reason>\n"
            "Example: /link 10.00 coffee fund"
        )
        return

    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    if amount <= 0:
        await update.message.reply_text("Amount must be greater than zero.")
        return

    reason = " ".join(context.args[1:])

    db = context.application.bot_data["db"]
    wallet_svc = WalletService(db)

    user = await wallet_svc.get_or_create_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )

    # Generate unique link code
    link_code = secrets.token_urlsafe(16)

    # Store in DB
    await db.create_payment_link(
        creator_id=user.telegram_id,
        amount=amount,
        reason=reason,
        link_code=link_code,
    )

    bot_username = (await context.bot.get_me()).username

    await update.message.reply_text(
        f"Payment Link Created!\n"
        f"{'=' * 25}\n"
        f"Amount: {format_usdc(amount)}\n"
        f"Reason: {reason}\n\n"
        f"Share this link:\n"
        f"https://t.me/{bot_username}?start=pay_{link_code}\n\n"
        f"Anyone with this link can request {format_usdc(amount)} from you."
    )
