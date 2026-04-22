"""/balance, /deposit, /withdraw command handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.wallet_service import WalletService
from bot.services.payment_service import PaymentService
from bot.models.payment import PaymentType
from bot.utils.formatting import format_usdc, format_address


async def _ensure_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ensure user is registered and return (wallet_svc, user)."""
    db = context.application.bot_data["db"]
    wallet_svc = WalletService(db)
    user = await wallet_svc.get_or_create_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )
    return wallet_svc, user


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance - check USDC balance on Arc testnet."""
    wallet_svc, user = await _ensure_user(update, context)

    usdc_balance = await wallet_svc.get_usdc_balance(user.wallet_address)

    msg = (
        f"<b>Your ArcPay Balance</b>\n"
        f"{'━' * 25}\n\n"
        f"💰 USDC: <b>{format_usdc(usdc_balance)}</b>\n\n"
        f"📍 Address:\n<code>{user.wallet_address}</code>\n\n"
        f"ℹ️ On Arc, USDC is the native gas token.\n"
        f"Fund your wallet at: https://faucet.circle.com\n"
        f"Select 'Arc Testnet' and paste your address above."
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deposit - show deposit address."""
    _, user = await _ensure_user(update, context)

    msg = (
        f"<b>Deposit USDC</b>\n"
        f"{'━' * 25}\n\n"
        f"Send USDC on <b>Arc Testnet</b> to:\n\n"
        f"<code>{user.wallet_address}</code>\n\n"
        f"🔗 Get testnet USDC:\n"
        f"1. Go to https://faucet.circle.com\n"
        f"2. Select <b>Arc Testnet</b>\n"
        f"3. Paste the address above\n"
        f"4. Request USDC\n\n"
        f"After funding, use /balance to check."
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /withdraw <address> <amount> - withdraw USDC to external address."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /withdraw <address> <amount>\n"
            "Example: /withdraw 0xABC...DEF 50.00"
        )
        return

    to_address = context.args[0]
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    if amount <= 0:
        await update.message.reply_text("Amount must be greater than zero.")
        return

    if not to_address.startswith("0x") or len(to_address) != 42:
        await update.message.reply_text("Invalid Ethereum address format.")
        return

    wallet_svc, user = await _ensure_user(update, context)
    db = context.application.bot_data["db"]
    payment_svc = PaymentService(db)

    balance = await wallet_svc.get_usdc_balance(user.wallet_address)
    if balance < amount:
        await update.message.reply_text(
            f"Insufficient balance. You have {format_usdc(balance)}."
        )
        return

    await update.message.reply_text(f"Withdrawing {format_usdc(amount)} USDC...")

    tx_hash = await payment_svc.send_usdc(
        from_user_id=user.telegram_id,
        to_user_id=0,
        from_address=user.wallet_address,
        to_address=to_address,
        amount=amount,
        encrypted_private_key=user.encrypted_private_key,
        memo="Withdrawal",
        payment_type=PaymentType.SEND,
    )

    if tx_hash:
        await update.message.reply_text(
            f"<b>Withdrawal successful!</b>\n\n"
            f"Amount: {format_usdc(amount)} USDC\n"
            f"To: <code>{to_address}</code>\n"
            f"Tx: <code>{tx_hash}</code>",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "Withdrawal failed. Please check your balance and try again."
        )
