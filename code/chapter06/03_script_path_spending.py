"""
Script Path Spending - Conditional Unlock

This script demonstrates Script Path spending in Taproot:
- Anyone who knows the preimage "helloworld" can spend
- Requires building control block to prove script legitimacy
- Witness structure: [preimage, script, control_block]

Reference: Chapter 6, Section "Phase 3: Reveal Phase - Script Path Spending" (lines 229-450)
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, P2trAddress
from bitcoinutils.script import Script
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.utils import to_satoshis, ControlBlock
import hashlib
import struct

def build_hash_lock_script(preimage):
    """Build Hash Lock script - same as commit phase"""
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    return Script([
        'OP_SHA256',
        preimage_hash,
        'OP_EQUALVERIFY',
        'OP_TRUE'
    ])

def script_path_spending():
    """
    Script Path spending - conditional unlock with preimage
    
    Unlike Key Path's simplicity, Script Path requires building more complex
    witness data to prove we have the right to use a specific script branch.
    """
    setup('testnet')

    print("=== PHASE 3: REVEAL PHASE - SCRIPT PATH SPENDING ===")
    print("Conditional unlock using Hash Lock script\n")
    
    # Step 1: Rebuild previous Taproot setup (must match commitment exactly!)
    alice_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    alice_public = alice_private.get_public_key()
    
    print("Step 1: Rebuild Taproot Setup")
    print(f"  ⚠️  CRITICAL: Must match commit phase exactly!")
    print(f"  Alice Private Key: {alice_private.to_wif()}")
    print(f"  Alice Public Key:  {alice_public.to_hex()}")
    
    # Step 2: Recreate same Hash Lock script
    preimage = "helloworld"
    tr_script = build_hash_lock_script(preimage)
    taproot_address = alice_public.get_taproot_address([[tr_script]])
    
    print(f"  Preimage: '{preimage}'")
    print(f"  Hash Lock Script: {tr_script.to_hex()}")
    print(f"  Taproot Address:  {taproot_address.to_string()}")
    
    # Step 3: Build spending transaction structure
    # Note: After Key Path spent 3,900 sats, another transaction funded the escrow address with 5,000 sats
    # The input transaction (previous_txid) created the UTXO we're spending from
    # The Script Path spending transaction (reveal) TXID will be: 68f7c8f0ab6b3c6f7eb037e36051ea3893b668c26ea6e52094ba01a7722e604f
    previous_txid = "9e193d8c5b4ff4ad7cb13d196c2ecc210d9b0ec144bb919ac4314c1240629886"  # Transaction that funded escrow with 5,000 sats
    input_amount = 0.00005000  # 5000 satoshis
    output_amount = 0.00004000  # 4000 satoshis (1000 sats fee)
    
    print(f"\nStep 2: Transaction Setup")
    print(f"  Previous TXID (input): {previous_txid}")
    print(f"  ⚠️  Note: This is the transaction that created the 5,000 sats UTXO at escrow address")
    print(f"  ⚠️  Note: After Key Path spent 3,900 sats, this transaction funded escrow with 5,000 sats")
    print(f"  Expected Script Path Reveal TXID: 68f7c8f0ab6b3c6f7eb037e36051ea3893b668c26ea6e52094ba01a7722e604f")
    print(f"  (This is the REVEAL transaction itself, not a commit transaction)")
    print(f"  Input Amount:  {input_amount} BTC ({to_satoshis(input_amount)} satoshis)")
    print(f"  Output Amount: {output_amount} BTC ({to_satoshis(output_amount)} satoshis)")
    print(f"  Fee:           {input_amount - output_amount} BTC ({to_satoshis(input_amount - output_amount)} satoshis)")
    
    txin = TxInput(previous_txid, 0)
    # Set nSequence to 0xffffffff (disable RBF) to match on-chain transaction
    txin.sequence = struct.pack('<I', 0xffffffff)
    # Use fixed output address from actual on-chain transaction to match TXID
    # This is the output address from the real Script Path spending transaction
    output_address = P2trAddress('tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne')
    txout = TxOutput(
        to_satoshis(output_amount),
        output_address.to_script_pub_key()
    )
    tx = Transaction([txin], [txout], has_segwit=True)
    
    print(f"  Output Address: {output_address.to_string()}")
    print(f"  nSequence: 0xffffffff (disable RBF, matches on-chain transaction)")
    print(f"  ⚠️  Note: Using fixed output address and nSequence from actual on-chain transaction")
    
    # Step 4: CRITICAL - Build control block to prove script legitimacy
    print(f"\nStep 3: Control Block Construction")
    print(f"  ⚠️  CRITICAL: Control block proves script is in Merkle tree")
    print(f"  - Internal public key: Base key for script tree commitment")
    print(f"  - Script tree structure: [[tr_script]] (single leaf)")
    print(f"  - Script index: 0 (position in tree)")
    print(f"  - Parity flag: {taproot_address.is_odd()} (from address.is_odd())")
    
    control_block = ControlBlock(
        alice_public,           # Internal public key for verification
        [[tr_script]],          # Script tree structure (single leaf)
        0,                      # Script index in tree (0 for single leaf)
        is_odd=taproot_address.is_odd()  # Output key parity - get from address!
    )
    
    cb_hex = control_block.to_hex()
    print(f"  Control Block (hex): {cb_hex}")
    print(f"  Control Block Structure (33 bytes):")
    print(f"    - Byte 1: Leaf version (0xc0) + Parity flag (0x01)")
    print(f"    - Bytes 2-33: Internal public key (32 bytes)")
    print(f"    - For single leaf: No Merkle path needed")
    
    # Step 5: Prepare script execution input - the secret "helloworld"
    preimage_hex = preimage.encode('utf-8').hex()  # Convert to hex: "68656c6c6f776f726c64"
    
    print(f"\nStep 4: Script Input Preparation")
    print(f"  Preimage: '{preimage}'")
    print(f"  UTF-8 Bytes: {preimage.encode('utf-8')}")
    print(f"  Hexadecimal: {preimage_hex}")
    print(f"  ⚠️  Encoding: String → UTF-8 bytes → Hexadecimal")
    
    # Step 6: Build Script Path witness (ORDER MATTERS!)
    print(f"\nStep 5: Witness Construction")
    print(f"  ⚠️  CRITICAL: Witness order is [preimage, script, control_block]")
    print(f"  - Position [0]: Script execution input (preimage)")
    print(f"  - Position [1]: Revealed script content")
    print(f"  - Position [2]: Control block (cryptographic proof)")
    print(f"  ❌ Wrong: [control_block, script, preimage]")
    print(f"  ❌ Wrong: [script, preimage, control_block]")
    print(f"  ✅ Correct: [preimage, script, control_block]")
    
    script_path_witness = TxWitnessInput([
        preimage_hex,              # [0] Script execution input: the secret
        tr_script.to_hex(),        # [1] Revealed script content
        control_block.to_hex()     # [2] Control block: cryptographic proof
    ])
    
    tx.witnesses.append(script_path_witness)
    
    signed_tx = tx.serialize()
    
    print(f"\n=== SCRIPT PATH TRANSACTION ===")
    print(f"Transaction ID: {tx.get_txid()}")
    print(f"Expected TXID (from chain): 68f7c8f0ab6b3c6f7eb037e36051ea3893b668c26ea6e52094ba01a7722e604f")
    txid_match = tx.get_txid() == '68f7c8f0ab6b3c6f7eb037e36051ea3893b668c26ea6e52094ba01a7722e604f'
    print(f"TXID Match: {txid_match}")
    if txid_match:
        print(f"✅ SUCCESS! Transaction ID matches the on-chain transaction exactly!")
        print(f"   This transaction can be reproduced with identical parameters.")
    print(f"Signed Transaction: {signed_tx}")
    print(f"Transaction Size: {len(signed_tx) // 2} bytes")
    print(f"Virtual Size: {tx.get_vsize()} vbytes")
    
    print(f"\n=== WITNESS DATA ANALYSIS ===")
    print(f"Witness Stack:")
    print(f"  [0] {preimage_hex}  # Preimage")
    print(f"  [1] {tr_script.to_hex()}  # Script")
    print(f"  [2] {cb_hex}  # Control block")
    print(f"Total Witness Items: 3")
    print(f"Witness Size: Larger than Key Path (~170 bytes vs 64 bytes)")
    
    print(f"\n=== SCRIPT PATH CHARACTERISTICS ===")
    print(f"✅ Witness Data: 3 elements (input + script + control block)")
    print(f"✅ Transaction Size: ~234 bytes (vs ~153 bytes for Key Path)")
    print(f"✅ Privacy Level: Partial privacy, only exposes used script branch")
    print(f"✅ Verification: Control block verification + script execution")
    print(f"✅ Fee Cost: Medium cost (~50% additional overhead vs Key Path)")
    
    return tx


if __name__ == "__main__":
    tx = script_path_spending()
    
    print(f"\n{'='*70}")
    print("KEY IMPLEMENTATION DETAILS")
    print(f"{'='*70}")
    print("1. Control Block Structure:")
    print("   - Contains leaf version + parity flag (byte 1)")
    print("   - Contains internal public key (bytes 2-33)")
    print("   - For single leaf: No Merkle path siblings needed")
    print("\n2. Witness Data Order:")
    print("   - Bitcoin Core parses witness in fixed order")
    print("   - Position [n-1]: Control block (last element)")
    print("   - Position [n-2]: Script code (second to last)")
    print("   - Positions [0...n-3]: Input parameters for script execution")
    print("\n3. Preimage Encoding:")
    print("   - Bitcoin Script processes hexadecimal byte data")
    print("   - Strings must be UTF-8 encoded, then converted to hex")
    print("   - This ensures OP_SHA256 can correctly process input data")

