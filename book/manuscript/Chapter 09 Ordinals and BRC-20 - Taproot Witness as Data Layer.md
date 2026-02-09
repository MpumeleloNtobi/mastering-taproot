# Chapter 9: Ordinals and BRC-20 - Taproot Witness as Data Layer

## Why This Chapter Matters

Ordinals is not just a "cultural phenomenon"—it represents the first global-scale case study of **Taproot enabling witness to function as a data layer**.

From an engineering perspective, this chapter addresses:

- Why witness can carry arbitrary data
- How Taproot's removal of the 520-byte script limit changed the ecosystem
- How commit-reveal becomes "non-executable Tapscript envelopes" in Ordinals
- Why indexers are the protocol's core (not on-chain scripts)

These are all design spaces that Taproot's upgrade structurally enabled,
even if they were not the primary motivation of the proposal.

## The Evolution: From SegWit to Taproot Data Layer

### SegWit: Moving Authorization to Witness

SegWit (BIP 141) introduced the witness structure, moving authorization data out of scriptSig:

**Before SegWit (Legacy):**
```
scriptSig: <signature> <public_key>
Total: ~107 bytes (counted at full weight)
```

**After SegWit (P2WPKH):**
```
scriptSig: <empty>
witness: <signature> <public_key>
Total: ~107 bytes in witness (75% discount)
```

**Key limitation**: In P2WSH, Script still enforced the 520-byte push size limit
and the 10,000-byte overall script size limit.

### Taproot: Relaxing Script Limits into a Data Layer

Taproot (BIP 341/342) fundamentally changes this:

**Tapscript (BIP 342) Characteristics:**
- No explicit 520-byte push limit (effectively bounded by resource limits)
- No explicit 10,000-byte script size limit (bounded by block weight)
- No OP_CODESEPARATOR
- Witness can contain arbitrary data pushes

**Result**: Witness becomes a **general-purpose data container**,
bounded only by block weight and policy limits rather than Script Engine limits.

### The Technical Breakthrough

```
SegWit P2WSH:
├── Push size limit: 520 bytes (enforced by Script Engine)
├── Overall script size limit: 10,000 bytes
├── Witness: Authorization data only
└── Use case: Complex scripts with weight discount

Taproot Tapscript:
├── No explicit 520-byte push limit (effectively bounded by resource limits)
├── No explicit 10,000-byte script size limit (bounded by block weight)
├── Witness: Authorization + arbitrary data
└── Use case: Data storage in witness
```

This architectural change enables protocols like Ordinals to store arbitrary data in witness without Bitcoin's VM executing it.

## Commit-Reveal Pattern: Non-Executable Tapscript Envelopes

Ordinals leverages Taproot's commit-reveal pattern in a unique way:
**the data branch of the script is never executed by Bitcoin's VM** —
it is committed and revealed, but not interpreted.

### Traditional Commit-Reveal (Chapter 6)

In our Hash Lock example:
```
Commit: Taproot address with script tree
Reveal: Execute script path, VM validates script
```

The script **must execute successfully** for the spend to be valid.

### Ordinals Commit-Reveal (Non-Executable)

In Ordinals:
```
Commit: Taproot address with inscription script in leaf
Reveal: Spend script path, VM validates script structure
        BUT: the inscription data branch is skipped during execution and never interpreted.
```

The script **must be valid Tapscript and evaluate to true**,
but the inscription data lives in a branch that is never taken,
so it is stored in the witness but never executed by the VM.

### Why This Works

Bitcoin's Script Engine:
- Validates script syntax
- Executes the script
- **But**: Conditional branches that are false are skipped entirely

In an Ordinals inscription script:
```
OP_0 OP_IF <data> OP_ENDIF
```

The VM sees `OP_0` (false), so it skips everything until `OP_ENDIF`. The data is **in the witness** but **never executed or interpreted by consensus rules**.

## BRC-20: Token Protocol on Ordinals

BRC-20 is a token standard built on top of Ordinals inscriptions. It uses JSON data in inscriptions to define token operations.

### BRC-20 Operation Types

**1. Deploy:**
```json
{
  "p": "brc-20",
  "op": "deploy",
  "tick": "DEMO",
  "max": "21000000",
  "lim": "1000"
}
```

**2. Mint:**
```json
{
  "p": "brc-20",
  "op": "mint",
  "tick": "DEMO",
  "amt": "1000"
}
```

**3. Transfer:**
```json
{
  "p": "brc-20",
  "op": "transfer",
  "tick": "DEMO",
  "amt": "100"
}
```

In practice, these JSON objects are placed inside the same Tapscript envelope pattern described above,
and then committed/revealed through a two-transaction flow: a key-path **commit** transaction, and a script-path **reveal** transaction.

## Real On-Chain Analysis: BRC-20 Mint Transaction Pair

Let's analyze a real testnet transaction pair to understand how a single-leaf Taproot node is constructed and revealed.

### Transaction Overview

**Commit Transaction:** `515ddcfc2ddb5ebadb6be493a955e490c54d399cf2cc528cecc302e41f950aa0`
- Input: 2,400 sats from `tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne`
- Output 0: 1,046 sats to `tb1pe7dahu72sdy64u449nw3k8u36gptxvccgyvmqn0t02t8pcceym5seqqfsp` (temporary address)
- Output 1: 1,054 sats to `tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne` (change)
- Fee: 300 sats
- Witness: Single signature (Key Path spending)

**Reveal Transaction:** `2fc169a5eb2f096bc8e64cb946380869ee2a2099f67cc3d5e719fbe9fff57547`
- Input: 1,046 sats from `tb1pe7dahu72sdy64u449nw3k8u36gptxvccgyvmqn0t02t8pcceym5seqqfsp` (temporary address)
- Output: 546 sats to `tb1p060z97qusuxe7w6h8z0l9kam5kn76jur22ecel75wjlmnkpxtnls6vdgne`
- Fee: 500 sats
- Witness: Script Path (signature, script, control block)

### Commit Phase: Building the Single-Leaf Taproot Address

The commit phase creates a Taproot address with a single script leaf containing the BRC-20 inscription data.

**Key Code: Building the Inscription Script**

```python
from bitcoinutils.setup import setup
from bitcoinutils.script import Script
from bitcoinutils.keys import PrivateKey

setup('testnet')

# Initialize keys
private_key = PrivateKey.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
public_key = private_key.get_public_key()
key_path_address = public_key.get_taproot_address()  # Main address

# Build BRC-20 JSON
import json
MINT_JSON = {
    "p": "brc-20",
    "op": "mint",
    "tick": "DEMO",
    "amt": "1000"
}
brc20_json_str = json.dumps(MINT_JSON, separators=(',', ':'))
brc20_hex = brc20_json_str.encode('utf-8').hex()

# Build inscription script
inscription_script = Script([
    public_key.to_x_only_hex(),  # 32-byte public key
    "OP_CHECKSIG",               # Script must be valid
    "OP_0",                      # Push 0 (false)
    "OP_IF",                     # If false, skip to OP_ENDIF
    "6f7264",                    # "ord" protocol marker (3 bytes)
    "OP_1",                      # Content type length (1 byte)
    "746578742f706c61696e3b636861727365743d7574662d38",  # "text/plain;charset=utf-8" (24 bytes)
    "OP_0",                      # Push empty string
    brc20_hex,                  # BRC-20 JSON data (53 bytes)
    "OP_ENDIF"                   # End conditional
])

# Create temporary address with single-leaf script tree
temp_address = public_key.get_taproot_address([[inscription_script]])

print(f"Temp Address: {temp_address.to_string()}")
# Output: tb1pe7dahu72sdy64u449nw3k8u36gptxvccgyvmqn0t02t8pcceym5seqqfsp
```

**On-Chain Verification:**

The temporary address `tb1pe7dahu72sdy64u449nw3k8u36gptxvccgyvmqn0t02t8pcceym5seqqfsp` matches the commit transaction's first output, confirming that the inscription script was correctly constructed.

**Key Code: Building the Commit Transaction**

```python
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
import struct

# Calculate amounts
inscription_amount = 546 + 500  # min_output + reveal_fee
commit_fee = 300
utxo_amount = 2400
change_amount = utxo_amount - inscription_amount - commit_fee

# Build commit transaction
previous_txid = "45fdef1870124f8f9fd3ff6daf2cb975bb434e7fba57bf4324f75025afcca008"
tx_input = TxInput(previous_txid, 1)
tx_input.sequence = struct.pack('<I', 0xfffffffd)  # RBF enabled

outputs = [
    TxOutput(inscription_amount, temp_address.to_script_pub_key()),
    TxOutput(change_amount, key_path_address.to_script_pub_key())
]

commit_tx = Transaction([tx_input], outputs, has_segwit=True)

# Sign with Key Path (spending to temp address)
signature = private_key.sign_taproot_input(
    commit_tx,
    0,
    [key_path_address.to_script_pub_key()],
    [utxo_amount],
    script_path=False
)

commit_tx.witnesses.append(TxWitnessInput([signature]))

print(f"Commit TxID: {commit_tx.get_txid()}")
# Output: 515ddcfc2ddb5ebadb6be493a955e490c54d399cf2cc528cecc302e41f950aa0
```

**On-Chain Structure:**

The commit transaction uses **Key Path spending** to send funds to the temporary address. The witness contains only a single Schnorr signature, indicating that the UTXO is being spent via the key path (not the script path). The inscription data is committed in the address but not yet revealed.

> **Note:** The following code snippets are **educational minimal examples**.
> They are not byte-for-byte implementations of the current Ordinals/BRC-20 spec,
> but they accurately illustrate the Taproot commit-reveal and witness-as-data patterns.
> A full runnable BRC-20 commit/reveal example is available in
> `code/chapter09/1_commit_mint_brc20.py` and `code/chapter09/2_reveal_mint_brc20.py`.

### Reveal Phase: Spending via Script Path

The reveal phase spends from the temporary address using **Script Path spending**, which reveals the inscription script in the witness.

**On-Chain Witness Analysis:**

The reveal transaction's witness contains three elements:

1. **Signature:** `894bf65e9593b1ce18071d44325add446b91e4638271318f1980d432e5de88fb743fcf7c69a5a3e98ffe0306944ddc1e4ab38e4c525fb1e0846263183a6de375`
2. **Script:** `2050be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3ac0063036f72645118746578742f706c61696e3b636861727365743d7574662d3800357b2270223a226272632d3230222c226f70223a226d696e74222c227469636b223a2244454d4f222c22616d74223a2231303030227d68`
3. **Control Block:** `c150be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3`

**Script Structure Breakdown:**

The witness script (hex) decodes as:

| Byte(s) | Hex | Opcode/Data | Meaning |
|---------|-----|-------------|---------|
| 1 | 20 | OP_PUSHBYTES_32 | Push 32 bytes |
| 2-33 | 50be5fc4...bb4d3 | Public key | 32-byte internal public key |
| 34 | ac | OP_CHECKSIG | Verify signature |
| 35 | 00 | OP_0 | Push false (0) |
| 36 | 63 | OP_IF | Conditional start |
| 37 | 03 | OP_PUSHBYTES_3 | Push 3 bytes |
| 38-40 | 6f7264 | "ord" | Protocol marker |
| 41 | 51 | OP_PUSHNUM_1 | Push 1 (content type length) |
| 42 | 18 | OP_PUSHBYTES_24 | Push 24 bytes |
| 43-66 | 746578742f...7574662d38 | "text/plain;charset=utf-8" | Content type |
| 67 | 00 | OP_0 | Push empty string |
| 68 | 35 | OP_PUSHBYTES_53 | Push 53 bytes |
| 69-121 | 7b2270223a...2231303030227d | BRC-20 JSON | `{"p":"brc-20","op":"mint","tick":"DEMO","amt":"1000"}` |
| 122 | 68 | OP_ENDIF | Conditional end |

This structure matches the high-level template we introduced earlier:
a valid Tapscript branch guarded by `OP_CHECKSIG`, plus a never-taken `OP_0 OP_IF ... OP_ENDIF` data envelope.

The BRC-20 JSON embedded in the script is:
```json
{"p":"brc-20","op":"mint","tick":"DEMO","amt":"1000"}
```

**Control Block Analysis:**

The control block is 33 bytes:
- **First byte:** `0xc1` = `11000001` (binary)
  - Bit 0: Parity bit = 1 (odd y-coordinate)
  - Bits 1-7: Leaf version = `0xc0` (Tapscript)
- **Remaining 32 bytes:** Internal public key = `50be5fc44ec580c387bf45df275aaa8b27e2d7716af31f10eeed357d126bb4d3`

For a single-leaf tree, the control block contains only the parity bit, leaf version, and internal public key—no Merkle path is needed. This is the simplest possible Taproot script-path spend:
a single-leaf tree with no Merkle siblings, which makes it ideal as a didactic example before we move on to more complex MAST structures in later chapters.

**Key Code: Building the Reveal Transaction**

```python
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.utils import ControlBlock

# Rebuild inscription script (must match commit phase exactly)
# See "Key Code: Building the Inscription Script" above for full implementation
inscription_script = Script([...])  # Same as commit phase
temp_address = public_key.get_taproot_address([[inscription_script]])

# Build reveal transaction
commit_txid = "515ddcfc2ddb5ebadb6be493a955e490c54d399cf2cc528cecc302e41f950aa0"
tx_input = TxInput(commit_txid, 0)
tx_output = TxOutput(output_amount, key_path_address.to_script_pub_key())
reveal_tx = Transaction([tx_input], [tx_output], has_segwit=True)

# Sign with Script Path (revealing the inscription)
signature = private_key.sign_taproot_input(
    reveal_tx,
    0,
    [temp_address.to_script_pub_key()],
    [inscription_amount],
    script_path=True,
    tapleaf_script=inscription_script,
    tweak=False
)

# Build control block (single-leaf tree)
control_block = ControlBlock(
    public_key,
    [[inscription_script]],  # Single-leaf tree structure
    0,                        # Script index (0 for single leaf)
    is_odd=temp_address.is_odd()
)

# Build witness (Script Path)
reveal_tx.witnesses.append(TxWitnessInput([
    signature,
    inscription_script.to_hex(),
    control_block.to_hex()
]))

print(f"Reveal TxID: {reveal_tx.get_txid()}")
# Output: 2fc169a5eb2f096bc8e64cb946380869ee2a2099f67cc3d5e719fbe9fff57547
```

**On-Chain Verification:**

The reveal transaction uses **Script Path spending** to spend from the temporary address. The witness contains:
1. A Schnorr signature over the script path
2. The complete inscription script (revealing the BRC-20 JSON)
3. A 33-byte control block proving the script's legitimacy in the Taproot tree

Bitcoin's VM validates that:
- The script is valid Tapscript
- The signature is valid
- The control block proves the script is in the tree
- The `OP_0 OP_IF ... OP_ENDIF` block is syntactically correct

However, the VM **never executes** the data inside the `OP_IF` block because `OP_0` pushes false, causing the VM to skip to `OP_ENDIF`. The BRC-20 JSON is stored in the blockchain but never interpreted by Bitcoin's consensus layer. The script must evaluate to true (via `OP_CHECKSIG`), but the inscription data branch is never taken and never semantically interpreted by consensus rules.

> **Note:** The envelope format shown here reflects the current standard.
> Earlier versions used slightly different structures.
> For example, recent versions support parent-child inscriptions, allowing an inscription to reference a "parent" inscription by ID—a feature not present in the original envelope format.
> Always check the latest ord documentation for protocol updates.

## Exercise: Decode a Real Reveal Transaction

1. Use `bitcoin-cli getrawtransaction 2fc169a5eb2f096bc8e64cb946380869ee2a2099f67cc3d5e719fbe9fff57547 true` 
   (or fetch from a block explorer) to get the reveal transaction.

2. Extract the witness script (second element in witness array).

3. Manually decode the script bytes:
   - Identify the public key (first 32 bytes after 0x20)
   - Locate the `OP_0 OP_IF` boundary
   - Extract the BRC-20 JSON payload

4. Verify: Does the JSON match what the chapter shows?

5. Bonus: If you prefer a visual approach, you can load the same transaction into StackFlow
   and watch the execution skip over the `OP_0 OP_IF ... OP_ENDIF` payload.

## Why Indexers? Chain-On Data, Chain-Off Interpretation

BRC-20 and Ordinals protocols rely on **indexers**—off-chain services that parse on-chain data and maintain protocol state.

### The Division of Labor

**On-Chain (Bitcoin):**
- Stores inscription data in witness (immutable)
- Validates Tapscript structure
- Does NOT execute or interpret the data

**Off-Chain (Indexers):**
- Parse witness data to extract inscriptions
- Reconstruct satoshi ranges
- Maintain token balances and state
- Track transfers and ownership

### Indexer Responsibilities

**1. Inscription Extraction:**

Indexers scan witness data in Taproot transactions, looking for the `OP_0 OP_IF ... OP_ENDIF` pattern. When found, they extract:
- Protocol marker (e.g., "ord")
- Content type (e.g., "text/plain;charset=utf-8")
- Content data (e.g., BRC-20 JSON)

**2. Satoshi Range Tracking:**

- Each UTXO has a range of satoshis
- Inscriptions bind to specific satoshis
- Transfers move inscribed satoshis to new UTXOs

**3. State Management:**

- Token balances per address
- Mint limits and supply
- Transfer history

### Why This Architecture?

**Bitcoin's Design Philosophy:**
- Minimal on-chain logic
- Maximum flexibility for off-chain protocols
- Data immutability without execution overhead

**Indexer Benefits:**
- Can update protocol rules without consensus changes
- Faster state queries than full node scanning
- Enables complex protocols without bloating Bitcoin

**Trade-offs:**
- Requires trust in indexer (or run your own)
- State is not consensus-enforced
- Different indexers may disagree

### Indexer Consensus Divergence

For BRC-20 in particular, this indexer dependence is not an abstract concern—it has already shown up in production. The "Different indexers may disagree" trade-off is more significant than it may initially appear. For engineers building on BRC-20, this is one of the protocol's most critical risk points.

**Cursed Inscriptions Controversy:**

In ord 0.5.x and earlier, certain malformed inscriptions were skipped during indexing. Starting from ord 0.6.0, these "cursed" inscriptions were retroactively recognized, causing different indexers to assign different inscription numbers to the same satoshi. This divergence means:

- Indexer A (ord 0.5.x): Skips cursed inscription, assigns #1000 to next valid inscription
- Indexer B (ord 0.6.0+): Recognizes cursed inscription as #-1000, assigns #1000 to different inscription

**BRC-20 Balance Discrepancies:**

If indexer A considers a mint invalid (e.g., exceeds `lim`), while indexer B considers it valid, users will see different balances:
- Exchange using indexer A: User cannot deposit tokens
- Exchange using indexer B: User can deposit tokens

**No On-Chain Arbitration:**

Unlike RGB's client-side validation, BRC-20's "correctness" depends entirely on social consensus—which indexer the community chooses to trust. This is not a technical defect, but an architectural choice. Protocol designers must understand that:

| Scenario | ord indexer | Third-party indexer X | Consequence |
|----------|-------------|----------------------|-------------|
| Cursed inscription #-1000 | Recognized (v0.6+) | Not recognized | Different inscription ownership for same satoshi |
| Mint exceeds `lim` | Invalid | Some versions accept | Balance inconsistency |

In other words, BRC-20 correctness is ultimately a matter of **social and indexer consensus**, not Bitcoin consensus.
Protocol designers need to treat the indexer layer as part of their trust model, not an invisible implementation detail.

## Engineering Summary: Why This Is Taproot's Real Application

### The Architectural Innovation

Ordinals/BRC-20 demonstrate that Taproot's real innovation isn't just about **better scripts**—it's about **removing script limitations** to enable new design spaces.

**Before Taproot:**
- Scripts had strict size limits (520-byte push limit and 10,000-byte script size)
- Witness was for authorization only
- Data storage required creative workarounds

**After Taproot:**
- Scripts are no longer constrained by the legacy 520-byte / 10,000-byte limits,
  and are instead effectively bounded by block weight and resource limits
- Witness becomes a data layer
- Protocols can store arbitrary data without consensus changes

### The Commit-Reveal Pattern Evolution

**Traditional (Chapter 6):**
```
Commit: Script tree with executable conditions
Reveal: Execute one condition, VM validates
```

**Ordinals/BRC-20:**
```
Commit: Script tree with data envelope
Reveal: Reveal data, VM validates structure (not content)
```

### Why This Matters for Bitcoin

1. **Protocol Flexibility**: New protocols can emerge without consensus changes
2. **Data Immutability**: Once inscribed, data is permanently on-chain
3. **Economic Efficiency**: Witness data gets weight discount
4. **Privacy Preservation**: Taproot addresses look identical regardless of content

### The Policy Debate: Witness vs. OP_RETURN

Bitcoin Core v30 introduces standardness policy changes that relax historical OP_RETURN size limits
(raising the old ~80-byte standard limit toward a much higher ceiling).

This raises a question: if OP_RETURN becomes a viable data layer,
does it compete with Taproot witness?

**Key differences:**

- **OP_RETURN**: Provably unspendable, no UTXO set bloat, but historically limited
- **Taproot witness**: Creates spendable UTXO (even if dust), larger capacity, weight discount

The debate is ongoing. Some argue OP_RETURN is "cleaner" for pure data storage;
others argue witness-based inscriptions are economically aligned (pay for block space).

For protocol designers, the choice depends on:

1. Whether you need the data bound to a specific satoshi (Ordinals model)
2. Whether you want to avoid creating dust UTXOs
3. Economic considerations (witness discount vs. OP_RETURN full weight)

In practice, most Ordinals/BRC-20 implementations will likely continue using witness even after OP_RETURN limits are relaxed, because satoshi binding—the ability to attach data to a specific satoshi—is fundamental to the Ordinals model and cannot be replicated with OP_RETURN.

### The Indexer Architecture

The separation of **on-chain storage** and **off-chain interpretation** is a powerful pattern:

```
[Bitcoin Node] → [Raw Blocks] → [Indexer] → [Protocol State DB]
                                    ↓
                            [API / Explorer]
                                    ↓
                              [User Wallet]
```

- Bitcoin provides: Immutable data storage
- Indexers provide: Protocol logic and state
- Users choose: Which indexers to trust (or run their own)

This architecture enables complex protocols while keeping Bitcoin's consensus layer minimal.

## Conclusion

Ordinals and BRC-20 represent the first large-scale application of Taproot's witness-as-data-layer capability. They demonstrate:

1. **Witness as Data Layer**: Taproot's removal of script limits enables arbitrary data storage
2. **Non-Executable Envelopes**: Scripts can contain data that Bitcoin's VM never executes
3. **Indexer Architecture**: Off-chain interpretation of on-chain data enables flexible protocols
4. **Commit-Reveal Evolution**: The pattern adapts from executable scripts to data envelopes

This is not Bitcoin Script "doing NFTs"—this is Taproot opening a new design space where witness becomes a data layer, and protocols like Ordinals/BRC-20 are the first explorers.
