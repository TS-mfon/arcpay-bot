"""Formatting utilities for bot messages."""

from typing import Optional


def format_usdc(amount: float) -> str:
    """Format a USDC amount for display."""
    return f"${amount:,.2f} USDC"


def format_address(address: str, chars: int = 6) -> str:
    """Shorten an Ethereum address for display."""
    if len(address) <= chars * 2 + 2:
        return address
    return f"{address[:chars + 2]}...{address[-chars:]}"


def format_tx_hash(tx_hash: str, chars: int = 8) -> str:
    """Shorten a transaction hash for display."""
    if len(tx_hash) <= chars * 2 + 2:
        return tx_hash
    return f"{tx_hash[:chars + 2]}...{tx_hash[-chars:]}"


def escape_markdown(text: str) -> str:
    """Escape Telegram MarkdownV2 special characters."""
    special_chars = r"_*[]()~`>#+-=|{}.!"
    escaped = ""
    for char in text:
        if char in special_chars:
            escaped += f"\\{char}"
        else:
            escaped += char
    return escaped


def build_help_message() -> str:
    """Build the help message listing all commands."""
    return (
        "ArcPay Bot - Telegram P2P Payments\n"
        "====================================\n\n"
        "Wallet:\n"
        "  /balance - Check your USDC balance\n"
        "  /deposit - Show your deposit address\n"
        "  /withdraw <address> <amount> - Withdraw USDC\n\n"
        "Payments:\n"
        "  /send @user <amount> [memo] - Send USDC\n"
        "  /tip @user <amount> - Tip a user\n\n"
        "Requests:\n"
        "  /request @user <amount> <reason> - Request payment\n"
        "  /pay <id> - Fulfill a payment request\n\n"
        "Group:\n"
        "  /split <amount> <reason> @user1 @user2... - Split expense\n\n"
        "Links:\n"
        "  /link <amount> <reason> - Create a payment link\n\n"
        "History:\n"
        "  /history - View transaction history\n"
        "  /receipt <tx_hash> - Generate receipt image\n"
    )


def payment_confirmation(
    sender: str,
    recipient: str,
    amount: float,
    memo: Optional[str],
    tx_hash: Optional[str],
) -> str:
    """Build a payment confirmation message."""
    msg = (
        f"Payment Sent!\n"
        f"From: {sender}\n"
        f"To: {recipient}\n"
        f"Amount: {format_usdc(amount)}\n"
    )
    if memo:
        msg += f"Memo: {memo}\n"
    if tx_hash:
        msg += f"Tx: {format_tx_hash(tx_hash)}\n"
    return msg
