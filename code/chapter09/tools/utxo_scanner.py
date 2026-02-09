#!/usr/bin/env python3
"""
UTXO Scanner and Selector

Fetches unspent outputs from the Blockstream API and selects the best
candidate for funding a commit transaction.
"""

import requests

def get_available_utxos(address=None):
    """
    Fetch available UTXOs for an address from the Blockstream testnet API.
    
    Args:
        address: Bech32m address to query. Falls back to the default if None.
    
    Returns:
        list[dict]: Each entry contains txid, vout, amount, scriptpubkey,
                    scriptpubkey_address, and a human-readable note.
    """
    if address is None:
        # Default address (derived from the project private key)
        address = "tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne"
    
    url = f"https://blockstream.info/testnet/api/address/{address}/utxo"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        utxo_list = resp.json()
        utxos = []
        for u in utxo_list:
            # Fetch the full transaction to obtain the scriptPubKey
            tx_url = f"https://blockstream.info/testnet/api/tx/{u['txid']}"
            tx_resp = requests.get(tx_url, timeout=10)
            if tx_resp.status_code == 200:
                tx_data = tx_resp.json()
                vout_data = tx_data["vout"][u["vout"]]
                utxos.append({
                    "txid": u["txid"],
                    "vout": u["vout"],
                    "amount": u["value"],
                    "scriptpubkey": vout_data["scriptpubkey"],
                    "scriptpubkey_address": vout_data["scriptpubkey_address"],
                    "note": "API"
                })
            else:
                # Keep basic info even if the full tx fetch fails
                utxos.append({
                    "txid": u["txid"],
                    "vout": u["vout"],
                    "amount": u["value"],
                    "scriptpubkey": None,
                    "scriptpubkey_address": None,
                    "note": "API (scriptPubKey unknown)"
                })
        return utxos
    except Exception as e:
        print(f"[ERROR] Failed to fetch UTXOs: {e}")
        return []

def select_best_utxo(min_amount=1500, address=None):
    """
    Select the most suitable UTXO (largest value that meets the minimum).
    
    Args:
        min_amount: Minimum required value in sats
        address: Bech32m address to query. Falls back to the default if None.
    
    Returns:
        dict | None: The selected UTXO, or None if none qualifies.
    """
    utxos = get_available_utxos(address)
    
    print("=== Scan Available UTXOs ===")
    for i, utxo in enumerate(utxos):
        status = "OK" if utxo["amount"] >= min_amount else "too small"
        print(f"  {i+1}. {utxo['txid'][:16]}...:{utxo['vout']} = {utxo['amount']} sats - {utxo['note']} {status}")
    
    # Filter by minimum amount
    suitable_utxos = [u for u in utxos if u["amount"] >= min_amount]
    
    if not suitable_utxos:
        print(f"[ERROR] No UTXO with at least {min_amount} sats found")
        return None
    
    # Pick the largest one
    selected = max(suitable_utxos, key=lambda x: x["amount"])
    print(f"\nSelected UTXO: {selected['txid'][:16]}...:{selected['vout']} ({selected['amount']} sats)")
    print(f"Source: {selected['note']}")
    
    return selected

def show_utxo_list():
    """Print a detailed listing of all available UTXOs."""
    utxos = get_available_utxos()
    print("=== All Available UTXOs ===")
    for i, utxo in enumerate(utxos):
        print(f"  {i+1}. TxID: {utxo['txid']}")
        print(f"      Vout: {utxo['vout']}")
        print(f"      Amount: {utxo['amount']} sats")
        print(f"      Note: {utxo['note']}")
        print()

if __name__ == "__main__":
    show_utxo_list()
    print()
    selected = select_best_utxo(1500)
    if selected:
        print(f"\nRecommended: {selected['txid']}:{selected['vout']}")
