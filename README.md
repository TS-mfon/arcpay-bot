# ArcPay Bot - Telegram P2P Payment System

A Venmo-like payment bot inside Telegram, powered by Arc Network's USDC rails.

## Features

- **Embedded Wallets**: Auto-created encrypted wallets per Telegram user
- **Send USDC**: `/send @user <amount> [memo]`
- **Request Payments**: `/request @user <amount> <reason>` and `/pay <id>`
- **Split Expenses**: `/split <amount> <reason> @user1 @user2`
- **Payment Links**: `/link <amount> <reason>`
- **Tips**: `/tip @user <amount>`
- **Transaction History**: `/history`
- **Receipt Generation**: `/receipt <tx_hash>` (generates image receipts)

## Architecture

```
Telegram User <-> Bot (python-telegram-bot)
                   |
                   +-> SQLite (user data, tx history)
                   +-> Web3 (Arc RPC)
                   +-> ArcPayEscrow.sol (on-chain escrow)
```

## Setup

### Smart Contracts (Foundry)

```bash
cd contracts
forge install foundry-rs/forge-std --no-commit
forge install OpenZeppelin/openzeppelin-contracts --no-commit
forge build
forge test
```

### Deploy

```bash
cd contracts
forge script script/Deploy.s.sol --rpc-url $ARC_RPC_URL --broadcast
```

### Bot

```bash
pip install -r requirements.txt
python -m bot.main
```

### Docker

```bash
docker build -t arcpay-bot .
docker run --env-file .env arcpay-bot
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Create wallet and get started |
| `/help` | Show all commands |
| `/balance` | Check USDC balance |
| `/deposit` | Show deposit address |
| `/withdraw <address> <amount>` | Withdraw USDC to external address |
| `/send @user <amount> [memo]` | Send USDC to a Telegram user |
| `/request @user <amount> <reason>` | Request payment from a user |
| `/pay <id>` | Fulfill a payment request |
| `/history` | View transaction history |
| `/split <amount> <reason> @user1 @user2...` | Split expense among users |
| `/link <amount> <reason>` | Create a payment link |
| `/tip @user <amount>` | Tip a user |
| `/receipt <tx_hash>` | Generate a receipt image |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `ARC_RPC_URL` | Arc Network RPC endpoint |
| `USDC_CONTRACT_ADDRESS` | USDC token contract address |
| `ESCROW_CONTRACT_ADDRESS` | Deployed ArcPayEscrow contract |
| `WALLET_ENCRYPTION_KEY` | Fernet key for wallet encryption |
