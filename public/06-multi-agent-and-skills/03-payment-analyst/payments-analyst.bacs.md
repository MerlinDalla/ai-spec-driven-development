# payments-analyst · Bacs reference

> Loaded when **Bacs** (Direct Debit / Bacs Direct Credit) is in scope. Capability + enforceable rules. Cite `BACS-*` IDs. Edit in place, keep IDs stable.

## Capability
| Field | Value |
|-------|-------|
| Region | United Kingdom |
| Type | Direct Debit (pull) and Bacs Direct Credit (push) |
| Currency | **GBP only** |
| Identifiers | Sort code + account number; SUN (Service User Number); DDI / mandate |
| Message standard | Bacs (Standard 18 / file-based) |
| Settlement | **3-day processing cycle** (submission → processing → settlement) |
| Cutoff | Input day submission cutoff 22:30 on day 1 of the 3-day cycle |

## Rules
- **BACS-1** — GBP only; validate sort code + account number and the originator **SUN**.
- **BACS-2** — Respect the **3-day cycle** timeline; value/settlement dates derive from the cycle. Validate against the Bacs processing calendar (`DATE-R1`).
- **BACS-3** — Direct Debit requires a valid **DDI / mandate**; mandate lifecycle (set-up, amendment, cancellation) and AUDDIS/ADDACS advice handling are specified.
- **BACS-4** — Handle Bacs **return/advice messages** (ARUDD for unpaid DDs, ADDACS for mandate changes, AWACS) with reason codes, owning queue, and creditor notification (`EXC-R1`).
- **BACS-5** — Direct Debit Guarantee: errors in collection are refunded immediately and in full on customer request; the refund flow and indemnity claim are specified.
- **BACS-6** — File-based batch: batch validation, partial-failure handling (reject one item vs whole file), and idempotency on resubmission are specified (`DOWN-R2`).
- **BACS-7** — Screening / AML / reporting per `COMPLIANCE-*`.
