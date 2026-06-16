# payments-analyst · SEPA Credit Transfer (SCT) reference

> Loaded when **SEPA SCT** is in scope. Capability + enforceable rules. Cite `SEPA-SCT-*` IDs. Edit in place, keep IDs stable.

## Capability
| Field | Value |
|-------|-------|
| Region | EU/EEA + SEPA-reachable territories |
| Type | Credit transfer (push) |
| Currency | **EUR only** |
| Identifiers | IBAN (BIC only where still required) |
| Message standard | ISO 20022 `pain.001` (initiation), `pacs.008` (interbank) |
| Settlement | Next business day (D) per CSM/clearing |
| Availability | Business days (TARGET calendar) |
| Cutoff | 15:00 CET for same-day CSM cycle (STEP2); after cutoff settles next business day |

## Rules
- **SEPA-SCT-1** — Currency MUST be EUR. Non-EUR instructions are ineligible for SCT — route to SWIFT or reject (see `CCY-3R`).
- **SEPA-SCT-2** — Beneficiary identified by a valid **IBAN**; validate structure, country code, and check digits. Require BIC only where IBAN-only routing is insufficient.
- **SEPA-SCT-3** — Both PSPs must be **SEPA-reachable**; verify reachability before routing, else reject with reason.
- **SEPA-SCT-4** — Remittance info: structured or unstructured per scheme limits (unstructured max 140 chars). Flag truncation risk.
- **SEPA-SCT-5** — Value date / cutoff: instructions received after 15:00 CET settle the next TARGET business day. Validate value date against the TARGET calendar (`DATE-R1/R2`).
- **SEPA-SCT-6** — Charges are **SHA/SLEV** (shared, beneficiary receives full amount). OUR/BEN do not apply.
- **SEPA-SCT-7** — **Returns / recalls / R-transactions** follow the SEPA SCT rulebook windows: return within 5 TARGET business days, recall/request-for-recall-of-funds via the CSM. Specify each flow, time window, and required approvals (`EXC-R1/R2`).
- **SEPA-SCT-8** — Screen before release (`COMPLIANCE-1R`); raise the cross-border reporting obligation where applicable.
