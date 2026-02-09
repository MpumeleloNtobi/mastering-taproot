#!/usr/bin/env python3
"""
BRC-20 Configuration and Constants

Defines the private key, network, fee parameters, token metadata,
and inscription helpers used by the BRC-20 commit / reveal scripts.
"""

# Private key (testnet WIF)
PRIVATE_KEY_WIF = "cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT"

# Network
NETWORK = "testnet"

# Fee configuration (adjustable)
FEE_CONFIG = {
    "commit_fee": 300,      # Commit transaction fee (sats)
    "reveal_fee": 500,      # Reveal transaction fee (sats)
    "min_output": 546,      # Minimum output value to avoid dust
}

# BRC-20 token definitions
TOKEN_CONFIG = {
    "deploy": {
        "p": "brc-20",
        "op": "deploy", 
        "tick": "PEPO",
        "max": "21000000",
        "lim": "1000"
    },
    "mint": {
        "p": "brc-20",
        "op": "mint",
        "tick": "DEMO", 
        "amt": "1000"
    }
}

# Inscription envelope constants
INSCRIPTION_CONFIG = {
    "content_type": "text/plain;charset=utf-8",
    "content_type_hex": "746578742f706c61696e3b636861727365743d7574662d38",
    "ord_marker": "6f7264"  # "ord"
}

def get_brc20_json(op_type="deploy"):
    """Return the compact JSON string for a given BRC-20 operation."""
    if op_type not in TOKEN_CONFIG:
        raise ValueError(f"Unsupported operation type: {op_type}")
    
    import json
    return json.dumps(TOKEN_CONFIG[op_type], separators=(',', ':'))

def get_brc20_hex(op_type="deploy"):
    """Return the hex-encoded JSON payload for a given BRC-20 operation."""
    json_str = get_brc20_json(op_type)
    return json_str.encode('utf-8').hex()

def calculate_inscription_amount():
    """Calculate the amount (sats) to send to the temporary address."""
    return FEE_CONFIG["min_output"] + FEE_CONFIG["reveal_fee"]

if __name__ == "__main__":
    print("=== BRC-20 Configuration ===")
    print(f"Network: {NETWORK}")
    print(f"Deploy payload: {get_brc20_json('deploy')}")
    print(f"Mint payload: {get_brc20_json('mint')}")
    print(f"Inscription amount: {calculate_inscription_amount()} sats")
    print(f"Fee config: {FEE_CONFIG}")
