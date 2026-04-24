"""ArcPay Bot - Telegram P2P Payment System on Arc Network."""

import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler

from bot.config import TELEGRAM_BOT_TOKEN
from bot.db.database import Database
from bot.handlers.start import start_command, help_command, commands_command, BOT_COMMANDS
from bot.handlers.wallet import balance_command, deposit_command, withdraw_command
from bot.handlers.send import send_command
from bot.handlers.request import request_command, pay_command
from bot.handlers.history import history_command
from bot.handlers.split import split_command
from bot.handlers.link import link_command
from bot.handlers.tip import tip_command
from bot.handlers.receipt import receipt_command
from bot.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def post_init(application):
    """Initialize database after the bot's event loop is ready."""
    db = Database()
    await db.initialize()
    application.bot_data["db"] = db
    await application.bot.set_my_commands(
        [BotCommand(command, description) for command, description in BOT_COMMANDS]
    )
    logger.info("Database initialized")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok","bot":"arcpay"}')

    def log_message(self, *args):
        pass  # suppress


def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("commands", commands_command))
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
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    # Start health server BEFORE main (which blocks on polling)
    threading.Thread(target=start_health_server, daemon=True).start()
    main()
