#!/usr/bin/env python3
"""
BRC-20 MINT COMMIT Transaction Builder

Creates a commit transaction that sends funds to a temporary Taproot address
embedding the BRC-20 inscription script, preparing for the reveal step.

Workflow: commit (this script) -> broadcast -> wait for confirmation -> reveal
"""

from bitcoinutils.setup import setup
from bitcoinutils.script import Script
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.keys import PrivateKey

# Import project utilities
from tools.utxo_scanner import select_best_utxo
from tools.brc20_config import (
    PRIVATE_KEY_WIF, NETWORK, FEE_CONFIG, 
    get_brc20_hex, calculate_inscription_amount,
    INSCRIPTION_CONFIG, get_brc20_json
)

def create_mint_commit_transaction():
    """
    Create BRC-20 MINT COMMIT transaction.
    
    The commit transaction sends funds to a temporary Taproot address whose
    script tree contains the inscription data.  The inscription is NOT yet
    revealed on-chain — only a hash commitment exists at this stage.
    
    Returns:
        tuple: (commit_tx, temp_address, key_path_address) or (None, None, None) on failure
    """
    
    setup(NETWORK)
    
    print("=== Create BRC-20 MINT COMMIT Transaction ===")
    
    # Display MINT payload
    mint_json = get_brc20_json("mint")
    print(f"MINT data: {mint_json}")
    
    # Initialise keys
    private_key = PrivateKey.from_wif(PRIVATE_KEY_WIF)
    public_key = private_key.get_public_key()
    key_path_address = public_key.get_taproot_address()  # main (funding) address
    
    print(f"Private key WIF: {PRIVATE_KEY_WIF}")
    print(f"Public key: {public_key.to_hex()}")
    print(f"x-only pubkey: {public_key.to_x_only_hex()}")
    print(f"Main address: {key_path_address.to_string()}")
    
    # Select a UTXO large enough to cover inscription output + fee + dust-limit change
    inscription_amount = calculate_inscription_amount()
    min_utxo_amount = inscription_amount + FEE_CONFIG["commit_fee"] + 546  # reserve for change
    
    selected_utxo = select_best_utxo(min_utxo_amount)
    if not selected_utxo:
        print(f"[ERROR] No UTXO with at least {min_utxo_amount} sats available")
        return None, None, None
    
    # Build the inscription script (Ordinals envelope)
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
    
    # Derive the temporary address from a single-leaf script tree
    temp_address = public_key.get_taproot_address([[inscription_script]])
    
    print(f"\n=== Address Verification ===")
    print(f"Temporary address: {temp_address.to_string()}")
    print(f"MINT script hex: {inscription_script.to_hex()}")
    
    # Calculate amounts
    utxo_amount = selected_utxo["amount"]
    commit_fee = FEE_CONFIG["commit_fee"]
    change_amount = utxo_amount - inscription_amount - commit_fee
    
    print(f"\n=== Amount Breakdown ===")
    print(f"UTXO value: {utxo_amount} sats")
    print(f"Inscription output: {inscription_amount} sats (sent to temporary address)")
    print(f"Commit fee: {commit_fee} sats (miner fee)")
    print(f"Change: {change_amount} sats (returned to main address)")
    print(f"\nNote: Change is returned via a second output — nothing is burned.")
    
    if change_amount < 0:
        print(f"[ERROR] Insufficient funds — need at least {inscription_amount + commit_fee} sats")
        return None, None, None
    
    if change_amount < 546 and change_amount > 0:
        print(f"[WARN] Change too small ({change_amount} sats); absorbed into fee")
        commit_fee += change_amount
        change_amount = 0
    
    # Construct the transaction
    print(f"\n=== Build MINT COMMIT Transaction ===")
    
    tx_input = TxInput(selected_utxo["txid"], selected_utxo["vout"])
    
    outputs = [
        TxOutput(inscription_amount, temp_address.to_script_pub_key())
    ]
    
    # Append change output (returned to main address) if above dust
    if change_amount > 0:
        outputs.append(TxOutput(change_amount, key_path_address.to_script_pub_key()))
    
    commit_tx = Transaction([tx_input], outputs, has_segwit=True)
    
    # Sign the transaction
    # NOTE: We must sign against the scriptPubKey of the UTXO being spent,
    # which may differ from our current address if the UTXO was received elsewhere.
    try:
        from bitcoinutils.keys import P2trAddress
        
        if selected_utxo.get("scriptpubkey_address"):
            utxo_address_str = selected_utxo["scriptpubkey_address"]
            utxo_address = P2trAddress(utxo_address_str)
            script_pubkey_for_signing = utxo_address.to_script_pub_key()
            print(f"Using UTXO scriptPubKey for signing")
            print(f"   UTXO address: {utxo_address_str}")
            print(f"   ScriptPubKey: {selected_utxo.get('scriptpubkey', 'unknown')}")
        else:
            script_pubkey_for_signing = key_path_address.to_script_pub_key()
            print(f"[WARN] UTXO has no address info — falling back to current address scriptPubKey")
        
        signature = private_key.sign_taproot_input(
            commit_tx,
            0,
            [script_pubkey_for_signing],
            [utxo_amount]
        )
        
        commit_tx.witnesses.append(TxWitnessInput([signature]))
        
        print(f"MINT COMMIT transaction signed successfully")
        print(f"TxID: {commit_tx.get_txid()}")
        print(f"Size: {commit_tx.get_size()} bytes")
        print(f"Virtual size: {commit_tx.get_vsize()} vbytes")
        
        print(f"\n=== Output Details ===")
        print(f"Output 0: {inscription_amount} sats -> {temp_address.to_string()} (temporary address)")
        if change_amount > 0:
            print(f"Output 1: {change_amount} sats -> {key_path_address.to_string()} (change)")
        
        return commit_tx, temp_address, key_path_address
        
    except Exception as e:
        print(f"[ERROR] Signing failed: {e}")
        return None, None, None

def broadcast_mint_commit(commit_tx):
    """Display broadcast instructions for the signed commit transaction."""
    
    if not commit_tx:
        print("[ERROR] No valid MINT COMMIT transaction to broadcast")
        return
    
    print(f"\n" + "="*60)
    print(f"MINT COMMIT Transaction Ready")
    print(f"="*60)
    
    print(f"Raw hex: {commit_tx.serialize()}")
    print()
    print(f"Broadcast via bitcoin-cli:")
    print(f"bitcoin-cli -{NETWORK} sendrawtransaction {commit_tx.serialize()}")
    print()
    print(f"Broadcast online:")
    print(f"https://live.blockcypher.com/btc-{NETWORK}/pushtx/")
    print(f"https://blockstream.info/{NETWORK}/tx/push")
    print()
    print(f"After broadcasting, wait for at least 1 confirmation, then run 2_reveal_mint_brc20.py")

if __name__ == "__main__":
    # Create MINT COMMIT transaction
    commit_tx, temp_address, key_path_address = create_mint_commit_transaction()
    
    if commit_tx:
        # Persist key information for the reveal step
        commit_info = {
            "commit_txid": commit_tx.get_txid(),
            "temp_address": temp_address.to_string(),
            "key_path_address": key_path_address.to_string(),
            "inscription_amount": calculate_inscription_amount(),
            "operation": "mint"
        }
        
        import json
        with open("commit_mint_info.json", "w") as f:
            json.dump(commit_info, f, indent=2)
        
        print(f"\nMINT info saved to commit_mint_info.json")
        
        # Show broadcast instructions
        broadcast_mint_commit(commit_tx)
    else:
        print("[ERROR] MINT COMMIT transaction creation failed")
