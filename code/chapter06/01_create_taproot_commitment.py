"""
Create Taproot Commitment - Commit Phase

This script demonstrates the Commit phase of Taproot's Commit-Reveal pattern:
- Build Hash Lock script for conditional spending
- Create Taproot address with script tree commitment
- Generate intermediate/custody address to lock funds

Reference: Chapter 6, Section "Phase 1: Commit Phase - Build Intermediate Address to Lock Funds" (lines 92-158)
"""

from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
import hashlib

def build_hash_lock_script(preimage):
    """
    Build a Hash Lock Script – anyone who knows the preimage can spend
    
    Script: OP_SHA256 <hash> OP_EQUALVERIFY OP_TRUE
    """
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    return Script([
        'OP_SHA256',           # Calculate SHA256 of input
        preimage_hash,         # Expected hash to match against
        'OP_EQUALVERIFY',      # Verify hash equality or fail
        'OP_TRUE'              # Success condition
    ])

def create_taproot_commitment():
    """
    Create Taproot commitment with Hash Lock script
    
    This creates the "intermediate address" or "custody address" where funds are locked.
    External observers cannot distinguish this from a simple Taproot payment.
    """
    setup('testnet')

    print("=== PHASE 1: COMMIT PHASE ===")
    print("Building Taproot address with Hash Lock script commitment\n")
    
    # Step 1: Alice's internal key - the foundation for her dual-path control
    internal_private = PrivateKey('cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT')
    internal_public = internal_private.get_public_key()
    
    print("Step 1: Internal Key Setup")
    print(f"  Private Key: {internal_private.to_wif()}")
    print(f"  Public Key:  {internal_public.to_hex()}")
    print(f"  Public Key (x-only): {internal_public.to_hex()[2:]}")
    
    # Step 2: Build Hash Lock script for "helloworld" secret
    preimage = "helloworld"
    hash_lock_script = build_hash_lock_script(preimage)
    
    print(f"\nStep 2: Hash Lock Script Construction")
    print(f"  Preimage: '{preimage}'")
    preimage_hash = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    print(f"  Preimage Hash (SHA256): {preimage_hash}")
    print(f"  Script Hex: {hash_lock_script.to_hex()}")
    print(f"  Script Structure:")
    print(f"    - OP_SHA256: Calculate SHA256 of input")
    print(f"    - PUSH 32 bytes: {preimage_hash}")
    print(f"    - OP_EQUALVERIFY: Verify hash equality")
    print(f"    - OP_TRUE: Success condition")
    
    # Step 3: Generate Taproot address (commit script tree to blockchain)
    # This creates our "intermediate address" where funds will be locked
    taproot_address = internal_public.get_taproot_address([[hash_lock_script]])
    
    print(f"\nStep 3: Taproot Address Generation")
    print(f"  Script Tree Structure: [[hash_lock_script]] (single leaf)")
    print(f"  Taproot Address: {taproot_address.to_string()}")
    print(f"  ScriptPubKey: {taproot_address.to_script_pub_key().to_hex()}")
    print(f"  Format: OP_1 <32-byte-output-key>")
    
    print(f"\n=== COMMITMENT SUMMARY ===")
    print(f"✅ Intermediate Address Created: {taproot_address.to_string()}")
    print(f"✅ This address commits to Hash Lock script")
    print(f"✅ External observers cannot distinguish from simple payment")
    print(f"✅ Funds can be spent via:")
    print(f"   - Key Path: Alice's direct control (64-byte signature)")
    print(f"   - Script Path: Anyone with preimage 'helloworld'")
    
    return taproot_address, hash_lock_script, internal_private, internal_public


if __name__ == "__main__":
    taproot_address, hash_lock_script, internal_private, internal_public = create_taproot_commitment()
    
    print(f"\n{'='*70}")
    print("KEY TECHNICAL POINTS")
    print(f"{'='*70}")
    print("1. Script Serialization:")
    print(f"   {hash_lock_script.to_hex()}")
    print("   - a8: OP_SHA256")
    print("   - 20: PUSH 32 bytes")
    print("   - 936a185c...07af: SHA256('helloworld')")
    print("   - 88: OP_EQUALVERIFY")
    print("   - 51: OP_TRUE")
    print("\n2. TapLeaf Hash Calculation:")
    print("   - For single leaf: TapLeaf hash = Merkle root")
    print("   - Uses tagged_hash('TapLeaf', leaf_version + script_length + script)")
    print("\n3. Output Key Generation:")
    print("   - Formula: Q = P + H('TapTweak' || P || merkle_root) * G")
    print("   - Internal pubkey + tweak = Output key")
    print("   - Output key is embedded in ScriptPubKey as 32-byte x-only key")

