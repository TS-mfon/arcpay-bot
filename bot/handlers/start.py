"""/start and /help command handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.wallet_service import WalletService
from bot.utils.formatting import build_commands_message, build_help_message, format_address

BOT_COMMANDS = [
    ("start", "Create or view your wallet"),
    ("commands", "List available commands"),
    ("help", "Show detailed command usage"),
    ("balance", "Check your USDC balance"),
    ("deposit", "Show your deposit address"),
    ("withdraw", "Withdraw USDC"),
    ("send", "Send USDC to a user"),
    ("tip", "Tip a user"),
    ("request", "Request payment"),
    ("pay", "Pay a request by id"),
    ("split", "Split an expense"),
    ("link", "Create a payment link"),
    ("history", "View transaction history"),
    ("receipt", "Generate a receipt image"),
]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start - create or retrieve wallet."""
    db = context.application.bot_data["db"]
    wallet_svc = WalletService(db)

    user = await wallet_svc.get_or_create_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )

    welcome = (
        f"Welcome to ArcPay!\n\n"
        f"Your wallet has been created.\n"
        f"Address: {format_address(user.wallet_address)}\n\n"
        f"Send /deposit to see your full deposit address.\n"
        f"Send /help to see all commands.\n"
    )
    await update.message.reply_text(welcome)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help - show all commands."""
    await update.message.reply_text(build_help_message())


async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /commands - show compact command list."""
    await update.message.reply_text(build_commands_message())
