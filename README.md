# ArcPay Bot — P2P USDC Payments on Arc Testnet

A production-grade Telegram bot for sending, requesting, and splitting **USDC** payments on Arc Network testnet (chain ID 5042002).

## Key Fact: USDC is Native on Arc

On Arc Network, **USDC is the native gas token** (not an ERC20 contract). All transactions use simple native value transfers, like sending ETH on Ethereum.

- Balance queries use `eth_getBalance`
- Transfers are 21,000-gas value transfers
- USDC uses 18 decimals on Arc (same as ETH)

## Features

### Wallet
- `/balance` — Check your USDC balance
- `/deposit` — Show deposit address + faucet link
- `/withdraw <address> <amount>` — Withdraw to external address

### Payments
- `/send @user <amount> [memo]` — Send USDC to another Telegram user
- `/tip @user <amount>` — Quick tip in group chats
- `/receipt <tx_hash>` — Generate receipt image

### Requests
- `/request @user <amount> <reason>` — Request payment
- `/pay <request_id>` — Fulfill a request

### Group
- `/split <amount> <reason> @user1 @user2 ...` — Split an expense

### Links
- `/link <amount> [reason]` — Create a shareable payment link

### History
- `/history` — View your last 20 transactions

## How @username Resolution Works

Both sender and receiver must `/start` the bot first — this registers their Telegram username → wallet address mapping.

If the recipient hasn't started the bot:
> `@someone` hasn't registered with ArcPay yet. Ask them to `/start` first, or use `/withdraw <address>` directly.

## Getting Testnet USDC

1. Run `/deposit` to get your wallet address
2. Visit https://faucet.circle.com
3. Select **Arc Testnet**
4. Paste your address and request USDC

## Production Features

- Real on-chain transactions with receipt polling
- Dynamic gas pricing (10% buffer)
- Incoming payment notifications
- Deep-link payment links (`t.me/bot?start=pay_XXX`)
- Rate limiting
- Structured JSON logging
- Multi-stage Docker build
- Fernet-encrypted private keys

## Smart Contract

Optional `ArcPayEscrow` at `0x67aF28a3383b1c1343D7264EEc90a3aD87A7a72A` for on-chain payment requests.

## Setup

```bash
cp .env.example .env
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Paste as WALLET_ENCRYPTION_KEY
pip install -r requirements.txt
python -m bot.main
```

## Deploy to Render

1. Create Web Service from this repo
2. Docker runtime
3. Set env vars from `.env.example`
4. Deploy

## License

MIT
