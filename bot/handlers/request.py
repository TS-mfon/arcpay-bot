"""/request and /pay command handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.wallet_service import WalletService
from bot.services.request_service import RequestService
from bot.services.user_resolver import UserResolver
from bot.utils.formatting import format_usdc


async def request_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /request @user <amount> <reason>."""
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /request @username <amount> <reason>\n"
            "Example: /request @bob 50.00 dinner last night"
        )
        return

    payer_username = context.args[0]
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    if amount <= 0:
        await update.message.reply_text("Amount must be greater than zero.")
        return

    reason = " ".join(context.args[2:])

    db = context.application.bot_data["db"]
    wallet_svc = WalletService(db)
    request_svc = RequestService(db)
    resolver = UserResolver(db)

    # Get requester
    requester = await wallet_svc.get_or_create_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )

    # Resolve payer
    payer = await resolver.resolve_username(payer_username)
    if not payer:
        await update.message.reply_text(
            f"User {payer_username} not found. "
            f"They need to /start the bot first."
        )
        return

    # Create request
    req = await request_svc.create_offchain_request(
        requester_id=requester.telegram_id,
        payer_id=payer.telegram_id,
        amount=amount,
        reason=reason,
    )

    await update.message.reply_text(
        f"Payment Request Created!\n"
        f"{'=' * 25}\n"
        f"Request ID: #{req.id}\n"
        f"From: {requester.display_name}\n"
        f"To: {payer.display_name}\n"
        f"Amount: {format_usdc(amount)}\n"
        f"Reason: {reason}\n\n"
        f"Tell {payer.display_name} to run:\n"
        f"/pay {req.id}"
    )


async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pay <request_id> - fulfill a payment request."""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /pay <request_id>\n" "Example: /pay 1"
        )
        return

    try:
        request_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid request ID.")
        return

    db = context.application.bot_data["db"]
    wallet_svc = WalletService(db)
    request_svc = RequestService(db)

    # Get payer
    payer = await wallet_svc.get_or_create_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )

    # Get request
    req = await db.get_payment_request(request_id)
    if not req:
        await update.message.reply_text(f"Request #{request_id} not found.")
        return

    if req.payer_id != payer.telegram_id:
        await update.message.reply_text("This request is not addressed to you.")
        return

    if req.status.value != "pending":
        await update.message.reply_text(
            f"This request is already {req.status.value}."
        )
        return

    # Check balance
    balance = await wallet_svc.get_usdc_balance(payer.wallet_address)
    if balance < req.amount:
        await update.message.reply_text(
            f"Insufficient balance. You have {format_usdc(balance)}, "
            f"but the request is for {format_usdc(req.amount)}."
        )
        return

    # Get requester info
    requester = await db.get_user(req.requester_id)
    if not requester:
        await update.message.reply_text("Requester not found.")
        return

    await update.message.reply_text(
        f"Paying {format_usdc(req.amount)} to {requester.display_name}..."
    )

    tx_hash = await request_svc.fulfill_request(
        request_id=request_id,
        payer_address=payer.wallet_address,
        requester_address=requester.wallet_address,
        encrypted_private_key=payer.encrypted_private_key,
        amount=req.amount,
        payer_id=payer.telegram_id,
        requester_id=requester.telegram_id,
    )

    if tx_hash:
        await update.message.reply_text(
            f"Payment Fulfilled!\n"
            f"Request: #{request_id}\n"
            f"Amount: {format_usdc(req.amount)}\n"
            f"To: {requester.display_name}\n"
            f"Tx: {tx_hash}"
        )
    else:
        await update.message.reply_text(
            "Payment failed. Please check your balance and try again."
        )
