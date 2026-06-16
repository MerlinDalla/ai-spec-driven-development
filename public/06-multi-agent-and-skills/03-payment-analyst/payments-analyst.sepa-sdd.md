# payments-analyst · SEPA Direct Debit (SDD) reference

> Loaded when **SEPA SDD** (Core or B2B) is in scope. Capability + enforceable rules. Cite `SEPA-SDD-*` IDs. Edit in place, keep IDs stable.

## Capability
| Field | Value |
|-------|-------|
| Region | EU/EEA + SEPA-reachable |
| Type | Direct debit (pull) — Core and B2B variants |
| Currency | **EUR only** |
| Identifiers | IBAN; Creditor Identifier; Mandate reference (UMR) |
| Message standard | ISO 20022 `pain.008` / `pacs.003` |
| Settlement | Driven by due date + presentation timelines |
| Presentation lead time | D-1 (one TARGET business day before due date) for first, one-off, and recurrent collections |

## Rules
- **SEPA-SDD-1** — A valid **mandate (UMR + Creditor Identifier)** must exist and be referenced. Mandate lifecycle is specified: creation, amendment, cancellation, expiry (dormant after 36 months with no collection).
- **SEPA-SDD-2** — Respect **presentation lead times**: collections must be presented D-1 (one TARGET business day before the due date) for all collection types. Validate the due date against the TARGET calendar.
- **SEPA-SDD-3** — **Core vs B2B differ on refunds:** Core allows a refund right (8 weeks for authorised collections, 13 months for unauthorised); **B2B has no refund right** and requires debtor-bank mandate verification. Enforce the variant's refund window.
- **SEPA-SDD-4** — Handle **R-transactions** explicitly: reject, refusal, return, refund, reversal, revocation, request-for-cancellation. Each has an owning queue, time window, and reason code (`EXC-R1`).
- **SEPA-SDD-5** — Insufficient funds / account closed / mandate invalid → return with the correct reason code; creditor notification and retry policy are specified.
- **SEPA-SDD-6** — Screen and apply AML/reporting as per `COMPLIANCE-*`.
