# DD-8: Commit-Reveal & Dual-Layer Scripts — Bitcoin's Programming Paradigm

> **Related Chapters**: Ch 2–8 | **Prerequisite**: Chapter 4 (SegWit) recommended

## Introduction

Bitcoin Script looks like a single program. It isn't.

Underneath, two different architectures coexist:
- A philosophical **commit–reveal model** shared by all address types
- An engineering **dual-layer execution structure** introduced only in P2SH, P2WSH, and Taproot script-path

Most confusion about Bitcoin scripting comes from mixing these two concepts. This Deep Dive separates them cleanly, then maps every transaction type from this book onto the correct architecture — with real testnet transactions you can verify yourself.

## Part 1: The Universal Truth — Commit → Reveal

Every Bitcoin output — P2PKH, SegWit, Taproot — follows one rule:

```
Lock:   commit to a condition
Unlock: reveal a proof satisfying it
```

| Address Type | What is Committed | Chapter |
|---|---|---|
| P2PK | Raw public key | Ch 1 (Satoshi → Hal Finney) |
| P2PKH | `HASH160(pubkey)` | Ch 2 |
| P2SH | `HASH160(script)` | Ch 3 |
| P2WPKH | `HASH160(pubkey)` via witness | Ch 4 |
| P2WSH | `SHA256(script)` via witness | Ch 4 (concept), Ch 11 |
| Taproot | `internal_key + tweak(merkle_root)` | Ch 5–8 |

Commitments grow more abstract across Bitcoin's history. Privacy improves. Scripts expose less and less. But the core pattern never changes:

**Commit → Reveal → Execute**

This is a *conceptual model*, not an execution structure. Commit–reveal is the language; opcodes are the grammar.

## Part 2: Single-Layer vs Dual-Layer Execution

Commit–reveal is universal. Dual-layer execution is not.

Bitcoin has exactly two script *execution* architectures:

### Single-Layer Scripts

The unlocking data and locking script execute in **one step** — no script hash, no script extraction, no inner vs. outer.

Used by: **P2PK, P2PKH, P2MS, P2WPKH, Taproot key-path**

```
unlocking data (scriptSig / witness)
            ↓
locking script (scriptPubKey / implicit logic) executes directly
```

### Dual-Layer Scripts

The unlocking data first **proves a commitment** (outer layer), then **loads and executes a revealed script** (inner layer).

Used only by: **P2SH, P2WSH, Taproot script-path**

```
┌──────────────────────────────────┐
│      Outer Layer: Commitment     │
│  (scriptPubKey verifies a hash   │
│   or tweaked key)                │
└───────────────┬──────────────────┘
                │ passes
                ▼
┌──────────────────────────────────┐
│   Inner Layer: Script Execution  │
│  (redeemScript / witnessScript   │
│   / tapscript runs the logic)    │
└──────────────────────────────────┘
```

Only these three structures follow: unlock → reveal → **load script** → execute script.

This is why P2SH's `scriptPubKey` has no `OP_CHECKSIG`. All logic lives in the inner script.

## Part 3: Single-Layer in Action — Real Transactions

### Example 1: P2PKH (Chapter 2)

**Transaction**: [`bf41b474...8355`](https://blockstream.info/testnet/tx/bf41b47481a9d1c99af0b62bb36bc864182312f39a3e1e06c8f6304ba8e58355)

```
ScriptPubKey (locking):
  76 a9 14 c5b28d6bba91a2693a9b1876bcd3929323890fb2 88 ac
  OP_DUP OP_HASH160 <pubkey_hash_20bytes> OP_EQUALVERIFY OP_CHECKSIG

ScriptSig (unlocking):
  <signature_71bytes> <pubkey_33bytes>
  3044022055c309fe...047443d01  02898711e6bf63f5...674c8519
```

**Architecture**: Single-layer. ScriptSig pushes `<sig>` and `<pubkey>` onto the stack. ScriptPubKey runs `OP_DUP OP_HASH160 ... OP_CHECKSIG` directly against them. One pass, one layer, done.

**What was committed?** `HASH160(pubkey)` = `c5b28d6bba91a2693a9b1876bcd3929323890fb2`

**What was revealed?** The full public key `02898711...674c8519` and a signature proving ownership.

### Example 2: P2WPKH (Chapter 4)

**Transaction**: [`271cf628...e3e6`](https://blockstream.info/testnet/tx/271cf6285479885a5ffa4817412bfcf55e7d2cf43ab1ede06c4332b46084e3e6)

```
ScriptPubKey (locking):
  00 14 c5b28d6bba91a2693a9b1876bcd3929323890fb2
  OP_0 <pubkey_hash_20bytes>

ScriptSig: (empty)

Witness:
  [0] 3044022015098d26...9e33c0301  (signature, 71 bytes)
  [1] 02898711e6bf63f5...674c8519   (pubkey, 33 bytes)
```

**Architecture**: Single-layer. Nodes recognize the pattern `OP_0 <20 bytes>` and execute an implicit P2PKH-equivalent program against the witness data. There is no script hash. There is no revealed script. The witness carries only data (signature + public key), not code.

**Same commitment as P2PKH** — same public key hash `c5b28d6b...890fb2` — but the proof moves from ScriptSig to the witness, making it malleability-resistant (see DD-4).

### Example 3: Taproot Key Path (Chapter 5 / Chapter 8)

**Chapter 5 Transaction**: [`a3b4d038...2cb6`](https://blockstream.info/testnet/tx/a3b4d0382efd189619d4f5bd598b6421e709649b87532d53aecdc76457a42cb6)

**Chapter 8 Key Path Transaction**: [`1e518aa5...00da`](https://blockstream.info/testnet/tx/1e518aa540bc770df549ec9836d89783ca19fc79b84e7407a882cbe9e95600da)

```
ScriptPubKey (locking):
  51 20 <32-byte output_pubkey>
  OP_1 <output_pubkey>

ScriptSig: (empty)

Witness:
  [0] 7d25fbc9b98ee0eb...da99f3   (64-byte Schnorr signature)
```

**Architecture**: Single-layer. Pure signature verification — no script execution at all. A single 64-byte Schnorr signature verifies the tweaked key. The witness contains one element; the scriptPubKey contains one opcode and one key.

**The purest single-layer form in Bitcoin**: no hash check, no script loading, no opcode evaluation beyond `OP_1`. Just: "Does this signature match this key?"

Note: The Chapter 8 key-path transaction spends from a four-leaf script tree address (`tb1pjfdm902y2adr0...`). An observer sees **nothing** about the tree — the spending looks identical to a simple single-key Taproot payment. This is the power of key-path: it collapses dual-layer complexity into single-layer simplicity.

## Part 4: Dual-Layer in Action — Real Transactions

### Example 4: P2SH 2-of-3 Multisig (Chapter 3)

**Funding Transaction**: [`4b869865...ba5f`](https://blockstream.info/testnet/tx/4b869865bc4a156d7e0ba14590b5c8971e57b8198af64d88872558ca88a8ba5f)

**Spending Transaction**: [`e68bef53...d4e0`](https://blockstream.info/testnet/tx/e68bef534c7536300c3ae5ccd0f79e031cab29d262380a37269151e8ba0fd4e0)

```
ScriptPubKey (outer layer — locking):
  a9 14 dd81b5beb3d82082f6df88aea0ac23a1485cb0ca 87
  OP_HASH160 <script_hash_20bytes> OP_EQUAL

ScriptSig (unlocking — carries both proof and inner script):
  OP_0                              ← OP_CHECKMULTISIG bug workaround
  <alice_signature_71bytes>         ← 3044022069...7a6501
  <bob_signature_71bytes>           ← 3044022065f8...fd9e01
  <redeem_script_105bytes>          ← 5221028987...601153ae
```

**Architecture**: Dual-layer.

**Outer layer** — The node hashes the last element of ScriptSig (the redeem script) and checks:
```
HASH160(522102898711...601153ae) == dd81b5beb3d82082f6df88aea0ac23a1485cb0ca ?
```
✓ Match. The commitment is valid.

**Inner layer** — The node loads the redeem script and executes it as a new program:
```
OP_2 <alice_pubkey> <bob_pubkey> <carol_pubkey> OP_3 OP_CHECKMULTISIG
```
against the remaining ScriptSig data (`OP_0 <alice_sig> <bob_sig>`).

**What the outer scriptPubKey never contains**: `OP_CHECKSIG`, `OP_CHECKMULTISIG`, or any logic opcode. The outer layer's only job is to verify the hash commitment. All logic lives in the inner script.

### Example 5: Taproot Script Path — Single Leaf (Chapter 6)

**Transaction**: [`68f7c8f0...604f`](https://blockstream.info/testnet/tx/68f7c8f0ab6b3c6f7eb037e36051ea3893b668c26ea6e52094ba01a7722e604f)

```
ScriptPubKey (outer layer):
  51 20 <32-byte output_pubkey>
  OP_1 <output_pubkey>

Witness (carries proof + inner script):
  [0] 68656c6c6f776f726c64                    ← preimage ("helloworld")
  [1] a820936a185caaa266bb9cbe981e9e05cb78cd   ← tapscript (hash lock)
      732b0b3280eb944412bb6f8f8f07af8851
  [2] c150be5fc44ec580c387bf45df275aaa8b27e2   ← control block (33 bytes)
      d7716af31f10eeed357d126bb4d3
```

**Architecture**: Dual-layer.

**Outer layer** — The node parses the control block, computes the TapLeaf hash of the revealed script, applies the TapTweak, and checks:

```
internal_pubkey + TapTweak × G == output_pubkey ?
```

✓ Match. The script was committed to in the Taproot output.

**Inner layer** — The node loads the tapscript and executes it:
```
OP_SHA256 <expected_hash> OP_EQUALVERIFY OP_TRUE
```
against the witness stack data (`68656c6c6f776f726c64` → "helloworld").

**The control block is the Merkle proof** — it replaces P2SH's simple `HASH160` check with a full Merkle path verification (see DD-5 for details). But the architecture is the same: outer commitment verification → inner script execution.

### Example 6: Taproot Script Path — Four-Leaf Tree (Chapter 8)

**Multisig Transaction**: [`1951a3be...04a1`](https://blockstream.info/testnet/tx/1951a3be0f05df377b1789223f6da66ed39c781aaf39ace0bf98c3beb7e604a1)

```
Witness (Script 1 — 2-of-2 Multisig):
  [0] 31fa0ca7929dac01...575bc         ← Bob's Schnorr signature (64 bytes)
  [1] 22272de665b99866...21fa0         ← Alice's Schnorr signature (64 bytes)
  [2] 002050be5fc44ec5...5287          ← tapscript (OP_CHECKSIGADD multisig)
  [3] c050be5fc44ec580...f299e3        ← control block (97 bytes)
```

**Outer layer**: Parse 97-byte control block → extract internal pubkey + two sibling hashes → reconstruct Merkle root → verify `TapTweak(internal_pubkey, merkle_root) × G + internal_pubkey == output_pubkey`.

**Inner layer**: Execute the Tapscript multisig:
```
OP_0 <alice_x_only_pubkey> OP_CHECKSIGADD <bob_x_only_pubkey> OP_CHECKSIGADD OP_2 OP_EQUAL
```

The control block grew from 33 bytes (single leaf, Chapter 6) to 65 bytes (dual leaf, Chapter 7) to 97 bytes (four-leaf, Chapter 8) — each level adds one 32-byte sibling hash to the Merkle proof. But the dual-layer architecture is identical in all three cases.

## Part 5: The Commitment Types Compared

Here is the outer-layer commitment mechanism for each dual-layer type, using real hex from the book:

### P2SH (Chapter 3)

```
scriptPubKey:  OP_HASH160 dd81b5beb3d82082f6df88aea0ac23a1485cb0ca OP_EQUAL
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                          HASH160 of the 2-of-3 redeem script
redeemScript:  OP_2 <alice_pub> <bob_pub> <carol_pub> OP_3 OP_CHECKMULTISIG
```

Commitment: 20-byte hash of the script. Simple, compact, but limited to one script.

### P2WSH (conceptual)

```
scriptPubKey:  OP_0 <32-byte SHA256(witnessScript)>
witnessScript: (actual logic)
```

Commitment: 32-byte SHA256 of the script. Stronger collision resistance than P2SH's 20-byte HASH160. Script moves from ScriptSig to witness (malleability-resistant).

### Taproot Script Path (Chapters 6–8)

```
scriptPubKey:  OP_1 <32-byte output_pubkey>
               output_pubkey = internal_pubkey + TapTweak(internal_pubkey, merkle_root) × G
witness:       <stack...> <tapscript> <control_block>
```

Commitment: An **elliptic curve point** that encodes both a public key and a Merkle tree root. This is fundamentally different from P2SH/P2WSH's hash-based commitment:

| Property | P2SH | P2WSH | Taproot |
|---|---|---|---|
| Commitment type | HASH160 | SHA256 | EC point (tweaked key) |
| Commitment size | 20 bytes | 32 bytes | 32 bytes |
| Multiple scripts? | No | No | Yes (Merkle tree) |
| Key-path fallback? | No | No | Yes |
| Outer scriptPubKey reveals | "This is P2SH" | "This is P2WSH" | Nothing (looks like any Taproot) |

The outer script **never encodes logic** — only a fingerprint of logic. But Taproot's fingerprint is richer: it commits to an entire tree of scripts while simultaneously functioning as a public key.

## Part 6: Taproot's Dual Identity — One Address, Two Architectures

Taproot is unique: the **same address** can be spent via single-layer (key-path) or dual-layer (script-path).

Chapter 8's address `tb1pjfdm902y2adr08qnn4tahxjvp6x5selgmvzx63yfqk2hdey02yvqjcr29q` demonstrates this:

| Spending Method | TXID | Architecture | Witness |
|---|---|---|---|
| Key Path | `1e518aa5...00da` | **Single-layer** | [64-byte signature] |
| Script 0 (Hash Lock) | `1ba4835f...6845` | **Dual-layer** | [preimage, script, control_block] |
| Script 1 (Multisig) | `1951a3be...04a1` | **Dual-layer** | [bob_sig, alice_sig, script, control_block] |
| Script 2 (CSV) | `98361ab2...41ee` | **Dual-layer** | [bob_sig, script, control_block] |
| Script 3 (Sig) | `1af46d4c...71b9` | **Dual-layer** | [bob_sig, script, control_block] |

**Five transactions, one address, two fundamentally different execution paths.**

The key-path witness has exactly one element (a signature). Every script-path witness has at least three elements (stack data, tapscript, control block). An observer can distinguish them by counting witness elements — but crucially, if key-path is used, **no one can tell the address ever had scripts at all**.

This dual identity is Taproot's deepest design insight: the common case (key-path) gets maximum efficiency and privacy, while the uncommon case (script-path) retains full programmability.

## Part 7: Why This Distinction Matters

Failing to distinguish commit–reveal (philosophy) from dual-layer (mechanism) leads to confusion on five specific questions:

| Question | Answer (with architecture) |
|---|---|
| Why does P2SH's scriptPubKey have no `OP_CHECKSIG`? | Because the outer layer only verifies a hash commitment. Logic lives in the inner redeem script. |
| Why does SegWit move data to the witness? | To make the outer commitment malleability-resistant (DD-4). The architecture stays single-layer for P2WPKH. |
| Why must P2WSH and Taproot script-path reveal the full script? | Because the inner layer needs actual opcodes to execute. The outer layer only has a hash/point. |
| Why must Taproot reconstruct the tweaked key? | Because Taproot's outer commitment is an EC point, not a simple hash. Verification requires elliptic curve arithmetic. |
| Why is key-path spending "scriptless"? | Because key-path is single-layer — it never enters the inner execution layer. The script tree is invisible. |

With the correct architecture model, every design decision clicks into place.

## Part 8: The Unified Evolution

Mapping every address type in this book onto the two-axis model:

```
                    Single-Layer              Dual-Layer
                    ──────────               ──────────
Hash Commitment:    P2PKH (Ch 2)             P2SH (Ch 3)
                    P2WPKH (Ch 4)            P2WSH (Ch 4/11)

Key Commitment:     P2PK (Ch 1)                  —
                    Taproot key-path (Ch 5-8)     —

Tree Commitment:        —                   Taproot script-path (Ch 6-8)
```

The evolution of commitments across Bitcoin's history:

```
P2PK     →  commit(pubkey)                              Ch 1
P2PKH    →  commit(hash(pubkey))                        Ch 2
P2SH     →  commit(hash(script))                        Ch 3
P2WPKH   →  commit(hash(pubkey)) via witness            Ch 4
P2WSH    →  commit(sha256(script)) via witness          Ch 4
Taproot  →  commit(internal_key + tweak(merkle_root))   Ch 5–8
```

Each step makes the commitment more abstract. P2PK reveals the public key upfront. P2PKH hides it behind a hash. P2SH hides entire scripts behind a hash. Taproot hides a full Merkle tree of scripts behind an elliptic curve point — and offers a key-path escape hatch that reveals nothing at all.

But the core has never changed since block 0:

**Commit → Reveal → Execute**

This is the true architecture of Bitcoin programmability.

---

*All transactions referenced in this Deep Dive are on Bitcoin testnet. Verify them on any testnet block explorer, or run the corresponding code from Chapters 2–8 of this book.*
