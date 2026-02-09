#!/usr/bin/env python3
"""
BRC-20 MINT REVEAL Transaction Builder

Spends the temporary Taproot address created by the commit step, revealing
the inscription data on-chain via a script-path spend.

Prerequisite: Run 1_commit_mint_brc20.py first and ensure the commit
transaction is confirmed on the network.
"""

from bitcoinutils.setup import setup
from bitcoinutils.utils import ControlBlock
from bitcoinutils.script import Script
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.keys import PrivateKey

# Import project utilities
import json
from tools.brc20_config import (
    PRIVATE_KEY_WIF, NETWORK, FEE_CONFIG,
    get_brc20_hex, INSCRIPTION_CONFIG, get_brc20_json
)

def load_mint_commit_info():
    """Load commit info from the JSON file produced by step 1."""
    try:
        with open("commit_mint_info.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("[ERROR] commit_mint_info.json not found")
        print("Please run 1_commit_mint_brc20.py first to create the MINT COMMIT transaction")
        return None

def create_mint_reveal_transaction():
    """
    Create BRC-20 MINT REVEAL transaction.
    
    This script-path spend reveals the inscription envelope in the witness,
    making the BRC-20 mint visible to indexers.
    
    Returns:
        Transaction: Signed reveal transaction, or None on failure
    """
    
    setup(NETWORK)
    
    print("=== Create BRC-20 MINT REVEAL Transaction ===")
    
    # Load commit info
    commit_info = load_mint_commit_info()
    if not commit_info:
        return None
    
    # Validate operation type
    if commit_info.get("operation") != "mint":
        print("[ERROR] commit_mint_info.json does not contain a MINT operation")
        return None
    
    print(f"MINT COMMIT TxID: {commit_info['commit_txid']}")
    print(f"Temporary address: {commit_info['temp_address']}")
    print(f"Main address: {commit_info['key_path_address']}")
    print(f"Inscription value: {commit_info['inscription_amount']} sats")
    
    # Display MINT payload
    mint_json = get_brc20_json("mint")
    print(f"MINT data: {mint_json}")
    
    # Initialise keys
    private_key = PrivateKey.from_wif(PRIVATE_KEY_WIF)
    public_key = private_key.get_public_key()
    key_path_address = public_key.get_taproot_address()
    
    print(f"\n=== Address Verification ===")
    print(f"Derived main address: {key_path_address.to_string()}")
    print(f"Expected main address: {commit_info['key_path_address']}")
    
    if key_path_address.to_string() != commit_info['key_path_address']:
        print("[ERROR] Address mismatch — check private key")
        return None
    
    print("Address verification passed")
    
    # Rebuild the inscription script (must match commit step exactly)
    brc20_hex = get_brc20_hex("mint")
    inscription_script = Script([
        public_key.to_x_only_hex(),
        "OP_CHECKSIG", 
        "OP_0",
        "OP_IF",
        INSCRIPTION_CONFIG["ord_marker"],
        "OP_1",
        INSCRIPTION_CONFIG["content_type_hex"],
        "OP_0",
        brc20_hex,
        "OP_ENDIF"
    ])
    
    # Verify the temporary address can be reproduced
    temp_address = public_key.get_taproot_address([[inscription_script]])
    
    print(f"\n=== Script Verification ===")
    print(f"Derived temporary address: {temp_address.to_string()}")
    print(f"Expected temporary address: {commit_info['temp_address']}")
    
    if temp_address.to_string() != commit_info['temp_address']:
        print("[ERROR] Temporary address mismatch — check inscription script")
        return None
    
    print("MINT script verification passed")
    print(f"MINT script hex: {inscription_script.to_hex()}")
    
    # Calculate reveal output amount
    inscription_amount = commit_info['inscription_amount']
    reveal_fee = FEE_CONFIG['reveal_fee']
    output_amount = inscription_amount - reveal_fee
    
    print(f"\n=== MINT REVEAL Amount Breakdown ===")
    print(f"Input value: {inscription_amount} sats")
    print(f"Reveal fee: {reveal_fee} sats")
    print(f"Output value: {output_amount} sats")
    
    if output_amount < FEE_CONFIG['min_output']:
        output_amount = FEE_CONFIG['min_output']
        reveal_fee = inscription_amount - output_amount
        print(f"Adjusted fee to {reveal_fee} sats (ensuring output >= {FEE_CONFIG['min_output']} sats)")
    
    # Build the transaction
    print(f"\n=== Build MINT REVEAL Transaction ===")
    
    tx_input = TxInput(commit_info['commit_txid'], 0)
    tx_output = TxOutput(output_amount, key_path_address.to_script_pub_key())
    
    reveal_tx = Transaction([tx_input], [tx_output], has_segwit=True)
    
    print(f"Unsigned reveal tx: {reveal_tx.serialize()}")
    
    # Sign using script-path spend
    try:
        signature = private_key.sign_taproot_input(
            reveal_tx,
            0,
            [temp_address.to_script_pub_key()],
            [inscription_amount],
            script_path=True,
            tapleaf_script=inscription_script,
            tweak=False
        )
        
        print(f"Signature: {signature}")
        
        # Construct the control block
        # Second argument is the script tree; single leaf requires double-nested list
        control_block = ControlBlock(
            public_key,
            [[inscription_script]],  # script tree: single leaf
            0,                        # script index in tree (0 for single leaf)
            is_odd=temp_address.is_odd()
        )
        
        print(f"Control block: {control_block.to_hex()}")
        print(f"Parity bit: {temp_address.is_odd()}")
        
        # Assemble the witness stack: [signature, script, control_block]
        reveal_tx.witnesses.append(TxWitnessInput([
            signature,
            inscription_script.to_hex(),
            control_block.to_hex()
        ]))
        
        print(f"\nMINT REVEAL transaction signed successfully")
        print(f"TxID: {reveal_tx.get_txid()}")
        print(f"WTxID: {reveal_tx.get_wtxid()}")
        print(f"Size: {reveal_tx.get_size()} bytes")
        print(f"Virtual size: {reveal_tx.get_vsize()} vbytes")
        
        print(f"\n=== Output Details ===")
        print(f"Output 0: {output_amount} sats -> {key_path_address.to_string()} (mint inscription + tokens)")
        
        return reveal_tx
        
    except Exception as e:
        print(f"[ERROR] Signing failed: {e}")
        return None

def broadcast_mint_reveal(reveal_tx):
    """Display broadcast instructions for the signed reveal transaction."""
    
    if not reveal_tx:
        print("[ERROR] No valid MINT REVEAL transaction to broadcast")
        return
    
    print(f"\n" + "="*60)
    print(f"MINT REVEAL Transaction Ready")
    print(f"="*60)
    
    print(f"Raw hex: {reveal_tx.serialize()}")
    print()
    print(f"Broadcast via bitcoin-cli:")
    print(f"bitcoin-cli -{NETWORK} sendrawtransaction {reveal_tx.serialize()}")
    print()
    print(f"Broadcast online:")
    print(f"https://live.blockcypher.com/btc-{NETWORK}/pushtx/")
    print(f"https://blockstream.info/{NETWORK}/tx/push")
    print()
    print(f"Expected outcome:")
    print(f"- Transaction accepted by the network")
    print(f"- MINT inscription ID assigned")
    print(f"- BRC-20 token minted successfully")
    print(f"- Tokens credited to your wallet")

def check_dependencies():
    """Verify that required classes are available."""
    try:
        from bitcoinutils.utils import ControlBlock
        print("ControlBlock class available")
        return True
    except ImportError:
        print("[ERROR] ControlBlock class not available")
        print("Upgrade bitcoinutils: pip install --upgrade bitcoin-utils")
        return False

if __name__ == "__main__":
    # Check dependencies
    if not check_dependencies():
        exit(1)
    
    # Create MINT REVEAL transaction
    reveal_tx = create_mint_reveal_transaction()
    
    if reveal_tx:
        broadcast_mint_reveal(reveal_tx)
        
        print(f"\nImportant reminders:")
        print(f"- Ensure the MINT COMMIT transaction is confirmed before broadcasting")
        print(f"- After a successful reveal, your token balance will increase")
        print(f"- Use UniSat or a compatible wallet to check token balances")
        print(f"- Each MINT consumes one minting opportunity")
    else:
        print("[ERROR] MINT REVEAL transaction creation failed")
