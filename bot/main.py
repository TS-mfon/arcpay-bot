"""ArcPay Bot - Telegram P2P Payment System on Arc Network."""

import asyncio
import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
)

from bot.config import TELEGRAM_BOT_TOKEN
from bot.db.database import Database
from bot.handlers.start import start_command, help_command
from bot.handlers.wallet import balance_command, deposit_command, withdraw_command
from bot.handlers.send import send_command
from bot.handlers.request import request_command, pay_command
from bot.handlers.history import history_command
from bot.handlers.split import split_command
from bot.handlers.link import link_command
from bot.handlers.tip import tip_command
from bot.handlers.receipt import receipt_command

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application):
    """Initialize database after application startup."""
    db = Database()
    await db.initialize()
    application.bot_data["db"] = db
    logger.info("Database initialized")


def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment")

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("withdraw", withdraw_command))
    application.add_handler(CommandHandler("send", send_command))
    application.add_handler(CommandHandler("request", request_command))
    application.add_handler(CommandHandler("pay", pay_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("split", split_command))
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(CommandHandler("tip", tip_command))
    application.add_handler(CommandHandler("receipt", receipt_command))

    logger.info("ArcPay Bot starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
