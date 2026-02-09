# DD-5: Inside Taproot Control Blocks — Merkle Proofs, Ordering Rules, and Fee Optimization

> **Related Chapters**: Ch 6–8 | **Prerequisite**: Chapter 8 (Four-Leaf Script Tree)

## Introduction

In Chapters 6 through 8, we built Taproot script trees and spent from them. Each Script Path spending required a **Control Block** — a compact data structure embedded in the witness. But what exactly is a Control Block? Why is it exactly 97 bytes for a four-leaf tree? What happens if you rearrange the scripts?

This Deep Dive answers these questions by dissecting the four real Control Blocks from Chapter 8's testnet transactions, running ordering experiments that reveal BIP341's sorting design, and analyzing the fee and privacy trade-offs of different tree topologies.

## Part 1: Control Block = Merkle Proof

A Control Block is **a Merkle proof that a specific script was committed to in the Taproot address**. It provides everything a verifier needs to reconstruct the Merkle root from the executed script, without seeing any other scripts.

### Structure

```
[1 byte: version + parity] [32 bytes: internal pubkey] [32 bytes × k: Merkle path]
```

| Tree Type | Leaves | Depth (k) | Control Block Size |
|---|---|---|---|
| Single-leaf | 1 | 0 | 33 bytes |
| Dual-leaf | 2 | 1 | 65 bytes |
| Four-leaf (balanced) | 4 | 2 | 97 bytes |
| Eight-leaf (balanced) | 8 | 3 | 129 bytes |

**Each additional tree level adds exactly 32 bytes** — one sibling hash for the Merkle path.

## Part 2: Dissecting Chapter 8's Four Control Blocks

Chapter 8 built a four-leaf script tree at address `tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q` with this structure:

```
                 Merkle Root
                /            \
        Branch0              Branch1
        /      \             /      \
   Script0   Script1    Script2   Script3
  (Hash Lock)(Multisig)  (CSV)    (Sig)
```

All four Script Path transactions were broadcast on testnet. Let's parse every Control Block.

### Shared Fields

All four Control Blocks share:
- **Version + Parity**: `c0` (Tapscript version 0xc0, parity bit 0 → output key y-coordinate is even)
- **Internal Public Key**: `50be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3` (Alice's x-only pubkey)

### Four Control Blocks Side by Side

| Field | Script 0 (Hash Lock) | Script 1 (Multisig) | Script 2 (CSV) | Script 3 (Sig) |
|---|---|---|---|---|
| Sibling 1 | `63cb9e47...60def` | `fe78d852...f659e` | `2faaa677...cf9df` | `593d543a...8e4b9` |
| Sibling 1 is... | Script1 TapLeaf | Script0 TapLeaf | Script3 TapLeaf | Script2 TapLeaf |
| Sibling 2 | `da551975...299e3` | `da551975...299e3` | `d6ac4c01...d1210` | `d6ac4c01...d1210` |
| Sibling 2 is... | Branch1 hash | Branch1 hash | Branch0 hash | Branch0 hash |

**Key observations:**

1. **Scripts in the same branch share the same Sibling 2**: Script 0 and Script 1 (both in Branch0) share `da551975...` (Branch1's hash). Script 2 and Script 3 (both in Branch1) share `d6ac4c01...` (Branch0's hash).

2. **Sibling 1 is always the other leaf in the same branch**: Script 0's sibling is Script 1's TapLeaf hash, and vice versa.

3. **No script content is revealed** — only hashes. When you spend via Script 2, the verifier sees Script 2's code but only sees 32-byte hashes for Script 3, Script 0, and Script 1.

### Complete Hash Map

From cross-referencing all four Control Blocks, we can extract every intermediate hash in the tree:

```
TapLeaf Hashes:
  Script 0 (Hash Lock):  fe78d8523ce9603014b28739a51ef826f791aa17511e617af6dc96a8f10f659e
  Script 1 (Multisig):   63cb9e4776a1cbb195c5cf0cbdbb3110d308969353680e38ec5f446336b60def
  Script 2 (CSV):         593d543a01c2c3c16c950ed97dfb3f3a1025b4b66323ed6b2814a1fb61d8e4b9
  Script 3 (Simple Sig):  2faaa677cb6ad6a74bf7025e4cd03d2a82c7fb8e3c277916d7751078105cf9df

Branch Hashes:
  Branch0 (Script0 + Script1): d6ac4c0133faaf95feb8e5656367d882f250e23b3295cafcbc465779960d1210
  Branch1 (Script2 + Script3): da55197526f26fa309563b7a3551ca945c046e5b7ada957e59160d4d27f299e3
```

## Part 3: Step-by-Step Merkle Reconstruction

Let's walk through verifying Script 1's (Multisig) Control Block — the same transaction analyzed in Chapter 8 (TXID: `1951a3be...04a1`).

### Step 1: Parse Control Block

```python
cb_hex = "c050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3" \
         "fe78d8523ce9603014b28739a51ef826f791aa17511e617af6dc96a8f10f659e" \
         "da55197526f26fa309563b7a3551ca945c046e5b7ada957e59160d4d27f299e3"
cb = bytes.fromhex(cb_hex)

version_parity = cb[0]          # 0xc0
internal_pubkey = cb[1:33]      # Alice's x-only pubkey
sibling_1 = cb[33:65]           # Script 0's TapLeaf hash
sibling_2 = cb[65:97]           # Branch1's TapBranch hash
```

### Step 2: Calculate Script 1's TapLeaf Hash

```python
script1_hex = "002050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3" \
              "ba2084b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5ba5287"
script_bytes = bytes.fromhex(script1_hex)

# TapLeaf = tagged_hash("TapLeaf", leaf_version || compact_size(len) || script)
leaf_version = bytes([0xc0])
script_len = len(script_bytes).to_bytes(1, 'big')  # 37 bytes
tapleaf_data = leaf_version + script_len + script_bytes

script1_tapleaf = tagged_hash("TapLeaf", tapleaf_data)
# Result: 63cb9e4776a1cbb195c5cf0cbdbb3110d308969353680e38ec5f446336b60def
```

Cross-check: this matches Script 0's sibling_1 in the table above ✓

### Step 3: Rebuild Branch0

```python
script0_tapleaf = sibling_1  # fe78d8523ce9603014b28739a51ef826f791aa17511e617af6dc96a8f10f659e

# BIP341: sort lexicographically before concatenating
if script1_tapleaf < script0_tapleaf:
    branch0_data = script1_tapleaf + script0_tapleaf
else:
    branch0_data = script0_tapleaf + script1_tapleaf

# 63cb9e... < fe78d8... → script1_tapleaf goes first
branch0 = tagged_hash("TapBranch", branch0_data)
# Result: d6ac4c0133faaf95feb8e5656367d882f250e23b3295cafcbc465779960d1210
```

Cross-check: this matches Script 2/3's sibling_2 (Branch0 hash) ✓

### Step 4: Rebuild Merkle Root

```python
branch1 = sibling_2  # da55197526f26fa309563b7a3551ca945c046e5b7ada957e59160d4d27f299e3

# Sort again
if branch0 < branch1:
    root_data = branch0 + branch1
else:
    root_data = branch1 + branch0

# d6ac4c... < da5519... → branch0 goes first
merkle_root = tagged_hash("TapBranch", root_data)
```

### Step 5: Calculate TapTweak and Verify Address

```python
tap_tweak = tagged_hash("TapTweak", internal_pubkey + merkle_root)
# output_key = internal_pubkey + tap_tweak × G  (EC point addition)
# Encode as bech32m → tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q ✓
```

**The address matches.** This proves Script 1 was indeed committed to in the original Taproot output.

### Visualize with RootScope

You can verify this yourself using [RootScope](https://btcstudy.github.io/RootScope/) — an open-source Taproot Control Block reverse engineering tool. Paste the script content and Control Block from any of Chapter 8's transactions, and RootScope will visualize every step of the reconstruction process, from byte-level parsing to address generation.

## Part 4: The Sorting Rule — Why Order Doesn't Matter (Mostly)

BIP341 specifies that `TapBranch` always sorts its two children lexicographically:

```
TapBranch(a, b) = tagged_hash("TapBranch", min(a, b) || max(a, b))
```

This has profound implications. Let's verify with experiments using Chapter 8's scripts.

### Experiment 1: Swap Siblings Within a Branch

```python
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey
from bitcoinutils.script import Script
from bitcoinutils.transactions import Sequence
from bitcoinutils.constants import TYPE_RELATIVE_TIMELOCK
import hashlib

setup('testnet')

alice_priv = PrivateKey("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
bob_priv = PrivateKey("cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG")
alice_pub = alice_priv.get_public_key()
bob_pub = bob_priv.get_public_key()

# Build the four scripts (identical to Chapter 8)
hash0 = hashlib.sha256("helloworld".encode('utf-8')).hexdigest()
script0 = Script(['OP_SHA256', hash0, 'OP_EQUALVERIFY', 'OP_TRUE'])
script1 = Script(["OP_0", alice_pub.to_x_only_hex(), "OP_CHECKSIGADD",
                   bob_pub.to_x_only_hex(), "OP_CHECKSIGADD", "OP_2", "OP_EQUAL"])
seq = Sequence(TYPE_RELATIVE_TIMELOCK, 2)
script2 = Script([seq.for_script(), "OP_CHECKSEQUENCEVERIFY", "OP_DROP",
                   bob_pub.to_x_only_hex(), "OP_CHECKSIG"])
script3 = Script([bob_pub.to_x_only_hex(), "OP_CHECKSIG"])

# Original tree (Chapter 8)
tree_original = [[script0, script1], [script2, script3]]
addr_original = alice_pub.get_taproot_address(tree_original)

# Swap script0 and script1 within Branch0
tree_swap_siblings = [[script1, script0], [script2, script3]]
addr_swap_siblings = alice_pub.get_taproot_address(tree_swap_siblings)

print(f"Original:       {addr_original.to_string()}")
print(f"Swap siblings:  {addr_swap_siblings.to_string()}")
print(f"Same address?   {addr_original.to_string() == addr_swap_siblings.to_string()}")
```

**Expected output:**
```
Original:       tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q
Swap siblings:  tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q
Same address?   True
```

**Why?** `TapBranch(script0_leaf, script1_leaf)` sorts them before hashing. The order you pass to `get_taproot_address` doesn't change the Branch hash.

### Experiment 2: Swap Entire Branches

```python
# Swap Branch0 and Branch1
tree_swap_branches = [[script2, script3], [script0, script1]]
addr_swap_branches = alice_pub.get_taproot_address(tree_swap_branches)

print(f"Original:        {addr_original.to_string()}")
print(f"Swap branches:   {addr_swap_branches.to_string()}")
print(f"Same address?    {addr_original.to_string() == addr_swap_branches.to_string()}")
```

**Expected output:**
```
Original:        tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q
Swap branches:   tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q
Same address?    True
```

**Why?** The top-level `TapBranch(Branch0, Branch1)` also sorts. Swapping left and right branches produces the same Merkle root.

### Experiment 3: Change the Tree Topology

```python
# Unbalanced tree: script0 at depth 1, others at depth 2-3
tree_unbalanced = [script0, [script1, [script2, script3]]]
addr_unbalanced = alice_pub.get_taproot_address(tree_unbalanced)

print(f"Original (balanced):   {addr_original.to_string()}")
print(f"Unbalanced:            {addr_unbalanced.to_string()}")
print(f"Same address?          {addr_original.to_string() == addr_unbalanced.to_string()}")
```

**Expected output:**
```
Original (balanced):   tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q
Unbalanced:            tb1p...  (DIFFERENT address)
Same address?          False
```

**Why?** Changing the topology changes the intermediate branch hashes. `TapBranch(script0_leaf, TapBranch(script1_leaf, TapBranch(script2_leaf, script3_leaf)))` is a completely different computation than `TapBranch(TapBranch(script0_leaf, script1_leaf), TapBranch(script2_leaf, script3_leaf))`.

### Summary: What Changes the Address?

| Operation | Address Changes? | Reason |
|---|---|---|
| Swap siblings within a branch | **No** | TapBranch sorts children |
| Swap entire branches | **No** | Top-level TapBranch also sorts |
| Swap scripts across branches | **Yes** | Different intermediate hashes |
| Change tree topology | **Yes** | Different computation structure |

## Part 5: Why Does BIP341 Sort?

The sorting rule wasn't arbitrary. It solves a critical problem for **multi-party protocols**.

### The Lightning Network Problem

In a Lightning channel, Alice and Bob must independently construct the same Taproot address. If the address depended on left/right ordering, they'd need an extra communication round to agree on "who goes left." With sorting:

```python
# Alice builds:
tree_alice = [[alice_script, bob_script], [timeout_script, penalty_script]]

# Bob builds (different order):
tree_bob = [[bob_script, alice_script], [penalty_script, timeout_script]]

# Both get the SAME address — no coordination needed for ordering
```

### The Trade-off

Sorting means you **cannot encode information in the left/right position** of scripts. But Taproot doesn't need this — the script content itself carries all semantic meaning. The sorting rule eliminates an entire class of bugs (mismatched ordering) at zero cost.

## Part 6: Fee Optimization — Unbalanced Trees

Chapter 8 used a balanced tree where all four scripts have identical 97-byte Control Blocks. But what if one script is used 90% of the time?

### Control Block Sizes for Different Topologies

**Balanced tree** `[[s0, s1], [s2, s3]]`:

| Script | Depth | Control Block | Size |
|---|---|---|---|
| Script 0 | 2 | version + pubkey + sibling + branch | 97 bytes |
| Script 1 | 2 | version + pubkey + sibling + branch | 97 bytes |
| Script 2 | 2 | version + pubkey + sibling + branch | 97 bytes |
| Script 3 | 2 | version + pubkey + sibling + branch | 97 bytes |

**Unbalanced tree** `[s0, [s1, [s2, s3]]]`:

| Script | Depth | Control Block | Size |
|---|---|---|---|
| Script 0 | 1 | version + pubkey + sibling | **65 bytes** |
| Script 1 | 2 | version + pubkey + sibling + branch | 97 bytes |
| Script 2 | 3 | version + pubkey + sibling + branch + branch | **129 bytes** |
| Script 3 | 3 | version + pubkey + sibling + branch + branch | **129 bytes** |

### Cost Calculation

At a fee rate of 10 sat/vbyte:
- Balanced tree: any script costs ~97 × 0.25 = ~24.25 vbytes for the Control Block
- Unbalanced tree: Script 0 costs ~65 × 0.25 = ~16.25 vbytes (**saves ~8 vbytes = ~80 sats**)
- Unbalanced tree: Script 2/3 costs ~129 × 0.25 = ~32.25 vbytes (**costs extra ~8 vbytes = ~80 sats**)

> Note: Witness data has a 75% discount (weight = size × 1 for witness, vs × 4 for non-witness), so the vbyte impact is `control_block_bytes × 0.25`.

### Design Principle

**Put the most frequently used script at the shallowest depth.** If your application uses Script Path 0 in 90% of cases:

```
Expected cost (balanced):    97 × 0.25 = 24.25 vbytes  (always)
Expected cost (unbalanced):  0.9 × 16.25 + 0.1 × avg(24.25, 32.25, 32.25) = 17.50 vbytes
Savings: ~28% on average
```

Of course, **Key Path spending is always optimal** (no Control Block at all — just a 64-byte signature). The fee optimization only matters when Key Path isn't available.

## Part 7: Privacy Analysis — What Control Blocks Reveal

When you spend via Script Path, the Control Block is visible on-chain. What does it leak?

### Information Disclosed

| Information | Revealed? | Details |
|---|---|---|
| Executed script content | **Yes** | Witness includes the full script |
| Other scripts' content | **No** | Only 32-byte hashes (computationally hiding) |
| Internal public key | **Yes** | Bytes 1–32 of Control Block |
| Minimum tree depth | **Yes** | `(control_block_size - 33) / 32` |
| Upper bound on script count | **Yes** | Depth k → at most 2^k leaves |
| Exact number of scripts | **No** | Depth 2 could be 3 or 4 leaves |
| Tree topology | **Partially** | The Merkle path reveals the branch structure for the executed script, but not the full tree |

### Concrete Example from Chapter 8

When Script 1 (Multisig) is spent, an observer sees:
- The multisig script itself (Alice and Bob's public keys, OP_CHECKSIGADD logic)
- Alice's internal public key
- Two 32-byte hashes (sibling nodes)
- The tree has depth ≥ 2, so at least 3 scripts exist

The observer does **not** know:
- That Script 0 is a hash lock, Script 2 is a CSV timelock, or Script 3 is a simple signature
- Whether the tree has exactly 4 leaves or more (the other branches could have sub-trees)
- Any private keys other than what the executed script reveals

### Key Path: Maximum Privacy

Key Path spending reveals **nothing** about the script tree:
- No Control Block
- No script content
- No tree depth information
- Indistinguishable from a simple single-signature Taproot payment

This is why Chapter 8 emphasizes Key Path as the preferred spending method — it's both the cheapest and the most private.

## Part 8: RootScope — Visual Verification Tool

[RootScope](https://btcstudy.github.io/RootScope/) is an open-source tool for Taproot Control Block reverse engineering. It takes witness data from any on-chain Taproot Script Path transaction and visualizes the complete Merkle reconstruction process.

### How to Use with Chapter 8 Data

1. **Open** [btcstudy.github.io/RootScope/](https://btcstudy.github.io/RootScope/)
2. **Paste Script Content** (from witness): e.g., Script 3's hex `2084b5951609b76619a1ce7f48977b4312ebe226987166ef044bfb374ceef63af5ac`
3. **Paste Control Block** (from witness): the 97-byte hex from Chapter 8's transaction
4. **Select Network**: Testnet
5. **Click "Start Real Analysis"**

RootScope will display:
- **Step 1**: Control Block structure breakdown (version, parity, internal pubkey, sibling hashes)
- **Step 2**: TapLeaf hash calculation with formula and actual values
- **Step 3**: Branch reconstruction using the first sibling
- **Step 4**: Merkle Root reconstruction using the second sibling
- **Step 5**: TapTweak calculation, EC point addition, and final address generation

Every intermediate hash value is displayed, allowing you to verify the math yourself or compare with the hash map in Part 2 of this Deep Dive.

### Try All Four Scripts

Use each of Chapter 8's four Script Path transactions to see how the Control Block changes while the reconstructed address stays the same:

| Transaction | Script Content | TXID |
|---|---|---|
| Hash Lock (Script 0) | `a820936a...8851` | `1ba4835f...6845` |
| Multisig (Script 1) | `002050be...5287` | `1951a3be...04a1` |
| CSV Timelock (Script 2) | `52b27520...f5ac` | `98361ab2...41ee` |
| Simple Signature (Script 3) | `2084b595...f5ac` | `1af46d4c...71b9` |

All four reconstruct to the same address: `tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q` — proving they all originate from the same script tree commitment.

## Conclusion

The Control Block is deceptively simple — just a version byte, a public key, and some hashes. But it encodes a complete Merkle proof that ties a specific script to a Taproot address without revealing any other scripts. BIP341's sorting rule ensures that multiple parties can independently construct the same tree without coordinating script ordering. And the tree topology — balanced vs. unbalanced — creates a direct trade-off between fee optimization and uniform privacy.

Understanding Control Blocks at this level transforms Taproot from "an API to call" into "a data structure to reason about." When you design a real Taproot application, the questions are no longer just "which scripts do I need?" but also "how deep should each script sit?" and "what does the Control Block reveal to chain analysts?"

---

*For hands-on verification, try [RootScope](https://btcstudy.github.io/RootScope/) with any Taproot Script Path transaction — from Chapter 8's testnet examples or from Bitcoin mainnet.*
