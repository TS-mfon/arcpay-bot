"""User-facing Telegram error handling."""

from __future__ import annotations

import html
import logging
import traceback
from dataclasses import dataclass

from telegram import Update
from telegram.error import BadRequest, Forbidden, NetworkError, TimedOut
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ErrorGuide:
    title: str
    explanation: str
    next_steps: tuple[str, ...]


def support_code(error: BaseException) -> str:
    return hex(abs(hash((type(error).__name__, str(error)))) % 0xFFFFFF)[2:].upper().zfill(6)


def classify_error(error: BaseException) -> ErrorGuide:
    text = str(error).lower()

    if isinstance(error, (TimedOut, TimeoutError)) or "timeout" in text:
        return ErrorGuide(
            "Request timed out",
            "ArcPay waited too long for Telegram, Arc RPC, or the payment backend.",
            (
                "Retry the command in a minute.",
                "For payments, check /balance before retrying.",
                "If a transaction may have been sent, use /history before sending again.",
            ),
        )

    if isinstance(error, NetworkError) or "connection" in text or "rpc" in text or "dns" in text:
        return ErrorGuide(
            "Network or Arc RPC issue",
            "The bot could not reach a service needed for this payment action.",
            (
                "Retry shortly; RPC endpoints can be temporarily unavailable.",
                "Use /balance to confirm the wallet is reachable.",
                "If sending funds, check /history before retrying to avoid duplicate payments.",
            ),
        )

    if isinstance(error, BadRequest):
        return ErrorGuide(
            "Telegram response formatting issue",
            "Telegram rejected the bot response, usually because it was too long or had invalid formatting.",
            (
                "Retry with a shorter memo or reason.",
                "Use /commands to confirm the exact command syntax.",
                "For receipts, use /receipt <tx_hash> with only the transaction hash.",
            ),
        )

    if isinstance(error, Forbidden):
        return ErrorGuide(
            "Bot cannot reply here",
            "Telegram says ArcPay cannot message this chat.",
            (
                "Open the bot directly and press Start.",
                "If this is a group, re-add the bot or allow messages.",
            ),
        )

    if isinstance(error, (ValueError, TypeError)) or "invalid" in text or "usage:" in text:
        return ErrorGuide(
            "Command format problem",
            "A required value is missing or has the wrong format.",
            (
                "Run /commands for the full command list.",
                "Use /send @user <amount> [memo].",
                "Use /withdraw <address> <amount>.",
            ),
        )

    if "insufficient" in text or "balance" in text or "fund" in text:
        return ErrorGuide(
            "Insufficient balance",
            "Your wallet does not have enough USDC or gas for this action.",
            (
                "Run /balance to check your wallet.",
                "Run /deposit to get your deposit address.",
                "Retry after the deposit is confirmed.",
            ),
        )

    if "address" in text or "recipient" in text or "user not found" in text:
        return ErrorGuide(
            "Recipient or address issue",
            "ArcPay could not resolve the recipient or wallet address.",
            (
                "Check the @username or wallet address.",
                "Ask the recipient to run /start first if sending by Telegram username.",
                "For withdrawals, use a valid 0x address.",
            ),
        )

    if "request" in text or "payment" in text or "tx" in text or "transaction" in text:
        return ErrorGuide(
            "Payment processing issue",
            "The payment flow could not be completed safely.",
            (
                "Check /history before retrying.",
                "For payment requests, confirm the request ID with /history.",
                "If funds moved on-chain, use /receipt <tx_hash>.",
            ),
        )

    return ErrorGuide(
        "Unexpected ArcPay error",
        "The command failed unexpectedly, but the bot is still running.",
        (
            "Retry the command once.",
            "Run /commands to confirm the syntax.",
            "If it repeats, share the support code with the maintainer.",
        ),
    )


def format_error_message(error: BaseException, hint: str | None = None) -> str:
    guide = classify_error(error)
    code = support_code(error)
    lines = [
        f"<b>{html.escape(guide.title)}</b>",
        html.escape(guide.explanation),
        "",
        "<b>What to do next</b>",
    ]
    lines.extend(f"- {html.escape(step)}" for step in guide.next_steps)
    if hint:
        lines.extend(["", f"<b>Hint:</b> {html.escape(hint)}"])
    lines.extend(["", f"<b>Support code:</b> <code>{code}</code>"])
    return "\n".join(lines)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error or RuntimeError("Unknown error")
    code = support_code(error)
    logger.error(
        "Unhandled update error support_code=%s update=%r\n%s",
        code,
        update,
        "".join(traceback.format_exception(type(error), error, error.__traceback__)),
    )

    if not isinstance(update, Update):
        return
    target = update.effective_message
    try:
        if target:
            await target.reply_text(format_error_message(error), parse_mode="HTML")
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(format_error_message(error), parse_mode="HTML")
    except Exception:
        logger.exception("Failed to send user-facing error message support_code=%s", code)
