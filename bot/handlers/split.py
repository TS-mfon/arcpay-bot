"""/split command handler."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.wallet_service import WalletService
from bot.services.payment_service import PaymentService
from bot.services.request_service import RequestService
from bot.services.user_resolver import UserResolver
from bot.utils.formatting import format_usdc


async def split_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /split <amount> <reason> @user1 @user2 ...

    Creates payment requests from each mentioned user for their share.
    The total amount is split evenly among the sender and all mentioned users.
    """
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /split <amount> <reason> @user1 @user2 ...\n"
            "Example: /split 120.00 dinner @alice @bob @charlie\n\n"
            "The amount is split evenly among you and the mentioned users."
        )
        return

    try:
        total_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return

    if total_amount <= 0:
        await update.message.reply_text("Amount must be greater than zero.")
        return

    # Parse reason and usernames
    reason_parts = []
    usernames = []
    for arg in context.args[1:]:
        if arg.startswith("@"):
            usernames.append(arg)
        else:
            reason_parts.append(arg)

    if not usernames:
        await update.message.reply_text(
            "Please mention at least one user to split with.\n"
            "Example: /split 100 pizza @alice @bob"
        )
        return

    reason = " ".join(reason_parts) if reason_parts else "Split expense"

    db = context.application.bot_data["db"]
    wallet_svc = WalletService(db)
    request_svc = RequestService(db)
    resolver = UserResolver(db)

    # Get sender
    sender = await wallet_svc.get_or_create_user(
        telegram_id=update.effective_user.id,
        username=update.effective_user.username,
    )

    # Resolve all users
    resolved_users = []
    not_found = []
    for username in usernames:
        user = await resolver.resolve_username(username)
        if user:
            resolved_users.append(user)
        else:
            not_found.append(username)

    if not_found:
        await update.message.reply_text(
            f"Users not found: {', '.join(not_found)}\n"
            f"They need to /start the bot first."
        )
        return

    # Calculate split (including sender)
    num_people = len(resolved_users) + 1
    per_person = round(total_amount / num_people, 2)

    # Create requests for each user's share
    request_ids = []
    for user in resolved_users:
        req = await request_svc.create_offchain_request(
            requester_id=sender.telegram_id,
            payer_id=user.telegram_id,
            amount=per_person,
            reason=f"Split: {reason}",
        )
        request_ids.append((user, req))

    # Build response
    lines = [
        f"Expense Split Created!",
        f"{'=' * 25}",
        f"Total: {format_usdc(total_amount)}",
        f"Split {num_people} ways: {format_usdc(per_person)} each",
        f"Reason: {reason}",
        f"",
        f"Your share: {format_usdc(per_person)} (organizer)",
        f"",
        f"Requests sent:",
    ]

    for user, req in request_ids:
        lines.append(f"  {user.display_name}: {format_usdc(per_person)} (ID: #{req.id})")

    lines.append(f"\nEach user can pay with: /pay <id>")

    await update.message.reply_text("\n".join(lines))
