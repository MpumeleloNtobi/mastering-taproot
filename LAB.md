# Mastering Taproot Lab

<p align="center">
  <img src="images/Lab Logo.jpg" width="200">
</p>

An open, builder-focused lab for hands-on Taproot engineering.

The book is the entry point. Code and notebooks are the tools.  
The goal is reproducible Bitcoin Script engineering.

---

## What is the Lab

The Mastering Taproot Lab follows the [book manuscript](book/manuscript/) with structured engineering exercises.

You:

- read
- run code
- verify on testnet
- iterate

Interactive notebooks at  
https://bitcoincoding.dev  
extend the flow: modify parameters, re-run, inspect results.

This is not a lecture series.  
It is engineering practice.

The lab is ongoing and evolves as contributors explore new patterns.

---

## Cohorts

The lab runs in cohort-style cycles.

The current Mastering Taproot Lab cohort is hosted as part of the  
[Chaincode Labs BOSS Challenge 2026](https://bosschallenge.xyz/).

Reading the book in order is recommended. Recordings provide structured guidance.

**Month 1 — Foundations**

Four recorded sessions to connect key ideas from the book:

| Week | Date | Topic |
|------|------|-------|
| Week 1 | Feb 22 | From UTXO to Taproot (Ch 1–5 mental models & evolution) |
| Week 2 | Mar 1 | Hands-on Taproot Coding (Ch 5–8 tree construction, control blocks, script paths) |
| Week 3 | Mar 8 | Bitcoin Programming Patterns (commit–reveal, script design thinking) |
| Week 4 | Mar 15 | Frontier & Applications (RGB, Lightning, Silent Payments, BRC-20 from an engineering view) |

**Weekly checkpoints** — Structured exercises in [labs/](labs/): copy the template, answer in writing, submit PR. Clarity > length. Best submissions may be discussed in the next session.

**Month 2 — Builder Mode**

Month 2 will be more builder-oriented, with optional experiments and small projects. More details later.

---

## Learning Structure

| Phase | Content |
|------|--------|
| **Entry** | Chapters 1–5: keys, addresses, P2PKH, P2SH, SegWit, Taproot foundations |
| **Core** | Chapters 6–8: single-leaf, dual-leaf, four-leaf contracts; key vs script path |
| **Applications** | Chapters 9–12: Ordinals, RGB, Lightning, Silent Payments |

Each chapter workflow:

1. Read the manuscript  
2. Run the code in [code/](code/)  
3. Explore via bitcoincoding.dev  
4. Verify outputs on Bitcoin testnet  

---

## Tool Stack

Optional but useful tools from the Mastering Taproot Lab toolkit:

• **btcaaron** (supported by OpenSats)  
https://github.com/aaron-recompile/btcaaron

• **StackFlow**  
https://btcstudy.github.io/bitcoin-script-simulator/

• **RootScope**  
https://btcstudy.github.io/RootScope/

These tools are designed for experimentation, inspection, and script-level understanding.

---

## How to Participate

1. **Weekly checkpoints** — [labs/](labs/) for structured questions; fork, copy template, submit PR  
2. Clone the repo or work from the manuscript  
3. Run examples from [code/](code/)  
4. Experiment on testnet  
5. Share findings via Issues or cohort channels  

Independent exploration is encouraged.

---

## Optional Projects

Ideas for extending the material:

- Port scripts to another language  
- Extend the Chapter 8 four-leaf tree  
- Build minimal tools using book patterns  
- Contribute translations in [book/translations/](book/translations/)

PRs welcome.

Precision and reproducibility over abstraction.

---

## Philosophy

Bitcoin engineering should be:

- reproducible  
- inspectable  
- forkable  

This lab exists to support that.

See also the repo [README](README.md) for project overview.
