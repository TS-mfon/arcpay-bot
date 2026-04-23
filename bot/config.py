"""Bot configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Arc Network / Web3
ARC_RPC_URL: str = os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network")
USDC_CONTRACT_ADDRESS: str = os.getenv("USDC_CONTRACT_ADDRESS", "")
ESCROW_CONTRACT_ADDRESS: str = os.getenv("ESCROW_CONTRACT_ADDRESS", "")

# Encryption
WALLET_ENCRYPTION_KEY: str = os.getenv("WALLET_ENCRYPTION_KEY", "")

# On Arc Network, USDC is the NATIVE gas token (chain id 5042002).
# The native token uses 18 decimals like ETH, NOT the 6 decimals
# used by USDC ERC20 tokens on Ethereum mainnet.
# So Web3.to_wei(amount, "ether") correctly converts USDC amounts.
USDC_DECIMALS: int = 18

# Arc chain config
ARC_CHAIN_ID: int = int(os.getenv("ARC_CHAIN_ID", "5042002"))
ARC_EXPLORER: str = os.getenv("ARC_EXPLORER", "https://testnet.arcscan.app")

# Database
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "arcpay.db")

# ERC-20 ABI (minimal for balanceOf, transfer, approve, transferFrom)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "transferFrom",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

# ArcPayEscrow ABI (minimal)
ESCROW_ABI = [
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "memo", "type": "string"},
        ],
        "name": "sendPayment",
        "outputs": [],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "recipients", "type": "address[]"},
            {"name": "amounts", "type": "uint256[]"},
            {"name": "memo", "type": "string"},
        ],
        "name": "batchSendPayment",
        "outputs": [],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "payer", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "reason", "type": "string"},
        ],
        "name": "createRequest",
        "outputs": [{"name": "requestId", "type": "uint256"}],
        "type": "function",
    },
    {
        "inputs": [{"name": "requestId", "type": "uint256"}],
        "name": "fulfillRequest",
        "outputs": [],
        "type": "function",
    },
    {
        "inputs": [{"name": "requestId", "type": "uint256"}],
        "name": "cancelRequest",
        "outputs": [],
        "type": "function",
    },
    {
        "inputs": [{"name": "requestId", "type": "uint256"}],
        "name": "getRequest",
        "outputs": [
            {
                "components": [
                    {"name": "id", "type": "uint256"},
                    {"name": "requester", "type": "address"},
                    {"name": "payer", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "reason", "type": "string"},
                    {"name": "expiresAt", "type": "uint256"},
                    {"name": "status", "type": "uint8"},
                    {"name": "createdAt", "type": "uint256"},
                ],
                "name": "",
                "type": "tuple",
            }
        ],
        "type": "function",
    },
]
