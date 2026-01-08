# Chapter 6: Building Real Taproot Contracts - Single-Leaf Hash Lock and Dual-Path Spending

This chapter demonstrates the complete implementation of Taproot's Commit-Reveal pattern through a practical Hash Lock contract example. You'll learn how to build single-leaf script trees, implement both Key Path and Script Path spending, and understand the privacy and efficiency trade-offs.

## Overview

This chapter covers:
- **Commit Phase**: Building Taproot addresses with script tree commitments
- **Key Path Spending**: Direct control using tweaked private keys (maximum privacy)
- **Script Path Spending**: Conditional unlock using script execution (selective reveal)
- **Verification**: Complete verification flow for Script Path spending

## Setup

### 1. Create Virtual Environment (if not already created)

```bash
cd code/chapter06
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## Scripts

### 01_create_taproot_commitment.py

**Purpose**: Demonstrates the Commit phase of Taproot's Commit-Reveal pattern.

**What it does**:
- Builds a Hash Lock script that requires the preimage "helloworld"
- Creates a Taproot address with script tree commitment
- Generates an intermediate/custody address to lock funds

**Key Concepts**:
- Script serialization: `OP_SHA256 <hash> OP_EQUALVERIFY OP_TRUE`
- TapLeaf hash calculation for single leaf
- Output key generation through tweaking

**Expected Output**:
- Taproot Address: `tb1p53ncq9ytax924ps66z6al3wfhy6a29w8h6xfu27xem06t98zkmvsakd43h`
- Script Hex: `a820936a185caaa266bb9cbe981e9e05cb78cd732b0b3280eb944412bb6f8f8f07af8851`

**Reference**: Chapter 6, Section "Phase 1: Commit Phase - Build Intermediate Address to Lock Funds" (lines 92-158)

**Run**:
```bash
python3 01_create_taproot_commitment.py
```

### 02_key_path_spending.py

**Purpose**: Demonstrates Key Path spending - Alice's direct control.

**What it does**:
- Rebuilds the same Taproot setup from commit phase
- Creates a transaction spending from the committed address
- Signs using Key Path (tweaked private key)
- Shows maximum privacy: only 64-byte Schnorr signature in witness

**Key Concepts**:
- Even for Key Path, script tree info is needed to calculate tweak
- Witness structure: `[signature]` (only 1 element)
- Identical appearance to simple Taproot payment

**Transaction Details**:
- Previous TXID: `4fd83128fb2df7cd25d96fdb6ed9bea26de755f212e37c3aa017641d3d2d2c6d`
- Input Amount: 0.00003900 BTC (3900 satoshis)
- Output Amount: 0.00003700 BTC (3700 satoshis)
- Fee: 0.00000200 BTC (200 satoshis)

**Reference**: Chapter 6, Section "Phase 2: Reveal Phase - Key Path Spending" (lines 160-227)

**Run**:
```bash
python3 02_key_path_spending.py
```

### 03_script_path_spending.py

**Purpose**: Demonstrates Script Path spending - conditional unlock with preimage.

**What it does**:
- Rebuilds the same Taproot setup (must match commit phase exactly!)
- Creates a transaction spending from the committed address
- Builds control block to prove script legitimacy
- Constructs witness with preimage, script, and control block

**Key Concepts**:
- Control Block: Proves script is in Merkle tree (33 bytes)
- Witness order: `[preimage, script, control_block]` (CRITICAL!)
- Preimage encoding: String → UTF-8 bytes → Hexadecimal

**Transaction Details**:
- Previous TXID: `68f7c8f0ab6b3c6f7eb037e36051ea3893b668c26ea6e52094ba01a7722e604f`
- Input Amount: 0.00005000 BTC (5000 satoshis)
- Output Amount: 0.00004000 BTC (4000 satoshis)
- Fee: 0.00001000 BTC (1000 satoshis)

**Witness Structure**:
```
[0] 68656c6c6f776f726c64  # Preimage ("helloworld")
[1] a820936a185c...8851   # Script
[2] c150be5fc4...bb4d3    # Control block
```

**Reference**: Chapter 6, Section "Phase 3: Reveal Phase - Script Path Spending" (lines 229-450)

**Run**:
```bash
python3 03_script_path_spending.py
```

### 04_verify_script_execution.py

**Purpose**: Provides verification functions for Script Path spending.

**What it does**:
- Verifies preimage content and hash calculation
- Verifies control block and proves script is in Merkle tree
- Verifies address restoration through tweak

**Key Functions**:
- `verify_preimage_and_script_execution()`: Verifies preimage decodes correctly and hash matches
- `verify_script_in_merkle_tree()`: Parses control block and verifies Merkle root
- `verify_taproot_address_restoration()`: Verifies address can be restored from internal key + script tree
- `verify_complete_script_path()`: Complete verification flow

**Reference**: Chapter 6, Section "Actual Transaction Execution Result Analysis" (lines 348-450)

**Run**:
```bash
python3 04_verify_script_execution.py
```

## Key Path vs Script Path Comparison

| Aspect | Key Path | Script Path |
|--------|----------|-------------|
| **Witness Data** | 1 element (64-byte signature) | 3 elements (input+script+control block) |
| **Transaction Size** | ~153 bytes | ~234 bytes |
| **Privacy Level** | Complete privacy, zero information leakage | Partial privacy, only exposes used script branch |
| **Verification Complexity** | Single Schnorr signature verification | Control block verification + script execution |
| **Fee Cost** | Lowest cost | Medium cost (~50% additional overhead) |

## Common Issues and Debugging

### 1. Witness Data Order Errors

**❌ Wrong**: `[control_block, script, preimage]`  
**❌ Wrong**: `[script, preimage, control_block]`  
**✅ Correct**: `[preimage, script, control_block]`

**Quick Fix**: Always remember "Data → Code → Proof" order for Script Path witnesses.

### 2. Script Serialization Issues

**❌ Wrong**: Direct use of strings
```python
script_hex = "OP_SHA256 936a185c... OP_EQUALVERIFY OP_TRUE"
```

**✅ Correct**: Use proper Script object and `.to_hex()`
```python
script = build_hash_lock_script(preimage)
script_hex = script.to_hex()  # Produces: "a820936a185c...8851"
```

### 3. Control Block Parity Errors

**❌ Wrong**: Manual calculation or hardcoded values
```python
is_odd = True  # Don't guess!
```

**✅ Correct**: Always get from address object
```python
is_odd = taproot_address.is_odd()
control_block = ControlBlock(..., is_odd=is_odd)
```

### 4. Commit-Reveal Inconsistency

**✅ Best Practice**: Use consistent helper functions
```python
def build_hash_lock_script(preimage):
    hash_value = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    return Script(['OP_SHA256', hash_value, 'OP_EQUALVERIFY', 'OP_TRUE'])

# Use SAME function in both commit and reveal phases
commit_script = build_hash_lock_script("helloworld")
reveal_script = build_hash_lock_script("helloworld")  # Guaranteed consistency
```

## Technical Details

### Control Block Structure

```
Control Block Structure (33 bytes):
┌─────────┬──────────────────────────────────┐
│ Byte 1  │           Bytes 2-33             │
├─────────┼──────────────────────────────────┤
│   c1    │ 50be5fc4...126bb4d3             │
├─────────┼──────────────────────────────────┤
│Ver+Parity│         Internal Pubkey          │
└─────────┴──────────────────────────────────┘

Analysis:
- c1 = c0 (leaf version) + 01 (parity flag)
- Internal pubkey: Used to recalculate output key during verification
```

### Tagged Hash

Tagged Hash prevents hash collisions between different protocols:

```python
def tagged_hash(tag, data):
    tag_hash = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(tag_hash + tag_hash + data).digest()

# Examples:
# tagged_hash("TapLeaf", script_data) for calculating script leaf hash
# tagged_hash("TapTweak", pubkey + merkle_root) for calculating tweak value
```

### Script Execution Flow

1. **OP_SHA256**: Calculate SHA256 of preimage input
2. **PUSH 32 bytes**: Push expected hash value
3. **OP_EQUALVERIFY**: Verify hash values equal
4. **OP_TRUE**: Push success flag (1)

## Chapter Summary

This chapter establishes the fundamental Commit-Reveal pattern for Taproot contracts:

1. **Commit Phase**: Commit complex conditional logic to an ordinary Taproot address
2. **Reveal Phase**: Choose Key Path or Script Path spending based on actual needs
3. **Selective Reveal**: Only expose necessary information, preserving maximum privacy

The power of this pattern: During Commit phase, all contracts of different complexity look identical; During Reveal phase, only the actually used branch needs to be exposed.

## Next Steps

In the following chapter, we'll explore **dual-leaf script trees**, learning how to organize multiple different spending conditions in one Taproot address, introducing real Merkle tree calculations, and experiencing the complete power of Taproot's script tree architecture.











