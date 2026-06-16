# payments-analyst · reference index

> The map of reference files the **payments-analyst** agent loads on demand. Files are siblings of the agent definition (`payments-analyst.agent.md`); paths are relative to this folder.
>
> **To add a scheme:** create `payments-analyst.<scheme>.md` (copy an existing one as a template) and add a row under *Load when in scope*. **To retire one:** remove its row. **To amend rules:** edit the scheme file in place, keeping rule IDs stable.

## Always load (every analysis)
| File | Contains |
|------|----------|
| `payments-analyst.currencies.md` | Supported currencies, minor units, FX & rounding rules (`CCY-*`) |
| `payments-analyst.compliance.md` | Sanctions screening, AML, regulatory reporting (`COMPLIANCE-*`) |

## Load when the scheme is in scope
| Scheme | File | Rule ID prefix | Currency | Type |
|--------|------|----------------|----------|------|
| SEPA SCT | `payments-analyst.sepa-sct.md` | `SEPA-SCT-*` | EUR | Credit transfer |
| SEPA SCT Inst | `payments-analyst.sepa-sct-inst.md` | `SEPA-INST-*` | EUR | Instant credit transfer |
| SEPA SDD | `payments-analyst.sepa-sdd.md` | `SEPA-SDD-*` | EUR | Direct debit |
| TARGET2 / T2 | `payments-analyst.target2.md` | `T2-*` | EUR | High-value RTGS |
| SWIFT cross-border | `payments-analyst.swift.md` | `SWIFT-*` | Multi | Credit transfer |
| CHAPS | `payments-analyst.chaps.md` | `CHAPS-*` | GBP | High-value RTGS |
| Faster Payments | `payments-analyst.fps.md` | `FPS-*` | GBP | Instant credit transfer |
| Bacs | `payments-analyst.bacs.md` | `BACS-*` | GBP | Direct debit / credit |
| ACH | `payments-analyst.ach.md` | `ACH-*` | USD | Batch credit / debit |
| Fedwire | `payments-analyst.fedwire.md` | `FEDWIRE-*` | USD | High-value RTGS |

## Out-of-scope schemes
The following are explicitly excluded so they aren't inadvertently assumed in scope: card schemes (Visa/Mastercard), crypto / stablecoin rails, cheque / paper instruments, cash, and intra-book (on-us book transfer) movements.
