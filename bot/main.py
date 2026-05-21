"""ArcPay Bot - Telegram P2P Payment System on Arc Network."""

import json
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, TypeHandler

from bot.config import TELEGRAM_BOT_TOKEN, WEBHOOK_BASE_URL
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
from bot.utils.errors import error_handler
from bot.utils.failover import (
    degraded_runtime_notice_handler,
    duplicate_guard_handler,
    finalize_update_handler,
    install_failover,
    runtime_health_payload,
    shutdown_failover,
)
from bot.utils.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def post_init(application):
    """Initialize database after the bot's event loop is ready."""
    db = Database()
    await db.initialize()
    application.bot_data["db"] = db
    await install_failover(application, "arcpay-bot", "ArcPay Bot")
    await application.bot.set_my_commands(
        [BotCommand(command, description) for command, description in BOT_COMMANDS]
    )
    logger.info("Database initialized")


async def post_shutdown(application):
    await shutdown_failover(application)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = runtime_health_payload("arcpay-bot", "ArcPay Bot")
        self.wfile.write(json.dumps(payload).encode("utf-8"))

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
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(TypeHandler(Update, duplicate_guard_handler), group=-100)
    application.add_handler(TypeHandler(Update, degraded_runtime_notice_handler), group=-90)

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
    application.add_handler(TypeHandler(Update, finalize_update_handler), group=1000)
    application.add_error_handler(error_handler)

    logger.info("ArcPay Bot starting...")
    webhook_base = WEBHOOK_BASE_URL.strip() or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    if webhook_base:
        token = TELEGRAM_BOT_TOKEN
        url_path = f"/telegram/{token}"
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", "10000")),
            url_path=url_path,
            webhook_url=f"{webhook_base}{url_path}",
            drop_pending_updates=True,
        )
        return

    threading.Thread(target=start_health_server, daemon=True).start()
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
