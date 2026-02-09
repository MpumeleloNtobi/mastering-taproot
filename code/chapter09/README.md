# Chapter 9: Ordinals and BRC-20 — Taproot Witness as Data Layer

This directory contains code examples for Chapter 9, demonstrating the complete commit-reveal workflow used by BRC-20 inscription protocols on Bitcoin.

## Overview

Inscription protocols embed arbitrary data into Bitcoin transactions using Taproot script-path spends. The process follows a **two-phase commit-reveal pattern**:

1. **Commit**: Send funds to a temporary Taproot address whose script tree contains the inscription data (only a hash commitment is visible on-chain).
2. **Reveal**: Spend from the temporary address via script-path, exposing the full inscription in the witness.

This chapter implements the BRC-20 mint workflow from scratch:

- **Commit** (`1_commit_mint_brc20.py`): Build inscription script, derive temporary address, sign key-path spend
- **Reveal** (`2_reveal_mint_brc20.py`): Rebuild script, sign script-path spend, reveal inscription on-chain

## Setup

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Files

### `1_commit_mint_brc20.py`
Creates a BRC-20 MINT commit transaction.

**What It Does:**
- Scans available UTXOs via the Blockstream API
- Builds an Ordinals inscription script (envelope format)
- Derives a temporary Taproot address from a single-leaf script tree
- Signs a key-path spend from the funding UTXO
- Outputs change back to the main address

**Inscription Script Structure:**
```
<x-only pubkey> OP_CHECKSIG
OP_0 OP_IF
  <"ord">
  OP_1
  <content-type: "text/plain;charset=utf-8">
  OP_0
  <BRC-20 JSON payload>
OP_ENDIF
```

**Run:**
```bash
python3 1_commit_mint_brc20.py
```

### `2_reveal_mint_brc20.py`
Creates a BRC-20 MINT reveal transaction.

**What It Does:**
- Loads commit info from `commit_mint_info.json`
- Rebuilds the inscription script and verifies address match
- Signs a script-path spend revealing the inscription on-chain
- Constructs witness: `[signature, script, control_block]`

**Witness Structure:**
- `[0]`: Schnorr signature (script-path, no sighash flag)
- `[1]`: Inscription script hex (the full Ordinals envelope)
- `[2]`: Control block (33 bytes — single leaf, no Merkle path needed)

**Run:**
```bash
python3 2_reveal_mint_brc20.py
```

## Tools (`tools/`)

### `brc20_config.py`
Configuration and constants for BRC-20 operations: private key, fee parameters, token metadata, and helpers for generating the JSON payload hex.

### `utxo_scanner.py`
Real-time UTXO scanner that queries the Blockstream testnet API. Fetches all UTXOs for a given address, retrieves the full `scriptPubKey` for each, and selects the largest UTXO meeting the minimum amount requirement.

## Key Technical Points

### Commit-Reveal Architecture

```
Phase 1: COMMIT (key-path spend)
┌────────────────┐         ┌──────────────────────┐
│  Funding UTXO  │────────▶│  Temporary Address   │
│  (main wallet) │         │  (script tree = hash  │
└────────────────┘         │   of inscription)     │
                           └──────────────────────┘

Phase 2: REVEAL (script-path spend)
┌──────────────────────┐         ┌──────────────────┐
│  Temporary Address   │────────▶│  Main Address     │
│  witness reveals:    │         │  (inscription +   │
│  [sig, script, cb]   │         │   tokens returned) │
└──────────────────────┘         └──────────────────┘
```

### Non-Executable Envelope

The inscription data lives inside an `OP_0 OP_IF ... OP_ENDIF` block. Bitcoin's VM sees `OP_0` (false), skips to `OP_ENDIF`, and never executes or interprets the data. The script evaluates to true via `OP_CHECKSIG`, but the payload is stored in the witness without being processed by consensus rules.

### Control Block (Single Leaf)

BRC-20 uses a single-leaf script tree:

| Field | Size | Description |
|-------|------|-------------|
| Version + parity | 1 byte | `0xc0` (even) or `0xc1` (odd) |
| Internal pubkey | 32 bytes | x-only public key |
| Merkle path | 0 bytes | No siblings for single leaf |
| **Total** | **33 bytes** | |

### UTXO Scanner

The `utxo_scanner.py` tool automates funding for the commit transaction:

1. Queries `blockstream.info/testnet/api/address/{addr}/utxo` for all UTXOs
2. Fetches the full transaction for each UTXO to extract its `scriptPubKey`
3. Selects the largest UTXO that meets the minimum amount (inscription + fees)
4. Returns UTXO metadata including txid, vout, value, and scriptPubKey address

This allows the scripts to run end-to-end on testnet without manual UTXO lookup.

## Tested Transactions

### BRC-20 MINT (Commit + Reveal)
- **Commit TxID**: `27d3a49f7a407002fc0aa84b2e9f6268ac8486107c207b59c8d56f18f75137f3`
- **Reveal TxID**: `ec9032fcbfa684fef4ef737aa5e64fbc5594122a75f81cdfe7ba413ac1373e6a`
- Token: DEMO, Amount: 1000

## Common Issues

### "Invalid Schnorr signature" on Broadcast
- The signing scriptPubKey must match the UTXO being spent
- If the UTXO belongs to a different address, the signature will be invalid
- The code automatically fetches and uses the correct scriptPubKey from the API

### Commit Must Confirm Before Reveal
- The reveal transaction spends output 0 of the commit transaction
- If the commit is not yet confirmed, the reveal will be rejected as spending a non-existent output
- Wait for at least 1 confirmation before broadcasting the reveal

### Testnet UTXO Availability
- The UTXO scanner queries `blockstream.info/testnet/api`
- Small UTXOs (below dust + fee threshold) are automatically skipped
- Fund the address with testnet coins if no suitable UTXO is found

## References

- Chapter 9: Ordinals and BRC-20 — Taproot Witness as Data Layer
- [BIP 341: Taproot](https://github.com/bitcoin/bips/blob/master/bip-0341.mediawiki)
- [BIP 342: Tapscript](https://github.com/bitcoin/bips/blob/master/bip-0342.mediawiki)
- [Ordinals / BRC-20 Documentation](https://docs.ordinals.com)
