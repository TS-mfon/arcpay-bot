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
    """Handle /balance - check USDC balance."""
    wallet_svc, user = await _ensure_user(update, context)

    usdc_balance = await wallet_svc.get_usdc_balance(user.wallet_address)
    eth_balance = await wallet_svc.get_eth_balance(user.wallet_address)

    msg = (
        f"Your Balance\n"
        f"{'=' * 20}\n"
        f"USDC: {format_usdc(usdc_balance)}\n"
        f"ARC (gas): {eth_balance:.6f}\n"
        f"\nAddress: {format_address(user.wallet_address)}"
    )
    await update.message.reply_text(msg)


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deposit - show deposit address."""
    _, user = await _ensure_user(update, context)

    msg = (
        f"Deposit Address\n"
        f"{'=' * 20}\n\n"
        f"{user.wallet_address}\n\n"
        f"Send USDC on Arc Network to this address.\n"
        f"Make sure you also send a small amount of ARC for gas fees."
    )
    await update.message.reply_text(msg)


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

    # Validate address format
    if not to_address.startswith("0x") or len(to_address) != 42:
        await update.message.reply_text("Invalid Ethereum address format.")
        return

    wallet_svc, user = await _ensure_user(update, context)
    db = context.application.bot_data["db"]
    payment_svc = PaymentService(db)

    # Check balance
    balance = await wallet_svc.get_usdc_balance(user.wallet_address)
    if balance < amount:
        await update.message.reply_text(
            f"Insufficient balance. You have {format_usdc(balance)}."
        )
        return

    await update.message.reply_text(f"Withdrawing {format_usdc(amount)}...")

    tx_hash = await payment_svc.send_usdc(
        from_user_id=user.telegram_id,
        to_user_id=0,  # external
        from_address=user.wallet_address,
        to_address=to_address,
        amount=amount,
        encrypted_private_key=user.encrypted_private_key,
        memo="Withdrawal",
        payment_type=PaymentType.SEND,
    )

    if tx_hash:
        await update.message.reply_text(
            f"Withdrawal successful!\n"
            f"Amount: {format_usdc(amount)}\n"
            f"To: {format_address(to_address)}\n"
            f"Tx: {tx_hash}"
        )
    else:
        await update.message.reply_text(
            "Withdrawal failed. Please check your balance and try again."
        )
