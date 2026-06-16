# payments-analyst · ACH (US) reference

> Loaded when **US ACH** is in scope. Capability + enforceable rules. Cite `ACH-*` IDs. Edit in place, keep IDs stable.

## Capability
| Field | Value |
|-------|-------|
| Region | United States |
| Type | Batch credit (push) and debit (pull) |
| Currency | **USD only** |
| Identifiers | ABA routing number + account number; SEC code |
| Message standard | Nacha file format |
| Settlement | Batch; same-day or next-day (D/D+1) per processing window |
| Cutoff | Same Day ACH submission windows 10:30 / 14:45 / 16:45 ET; standard ACH next-day |

## Rules
- **ACH-1** — USD only; validate **ABA routing number** (incl. check digit) + account number.
- **ACH-2** — Capture the correct **SEC code** (e.g., PPD, CCD, WEB, TEL) — it drives authorization, format, and return rules. Wrong SEC code is a validation failure.
- **ACH-3** — Distinguish **Same Day ACH** vs standard windows; enforce the relevant cutoff and the Same Day ACH per-transaction limit of USD 1,000,000.
- **ACH-4** — Handle **returns and NOCs** (return reason codes Rxx, Notification of Change) with time windows, owning queue, and originator notification (`EXC-R1`).
- **ACH-5** — Debit (pull) requires valid **authorization**; authorization capture/retention and unauthorized-return handling are specified.
- **ACH-6** — Batch/file processing: batch validation, partial-failure handling, and idempotency on resubmission are specified (`DOWN-R2`).
- **ACH-7** — OFAC sanctions screening and AML/reporting per `COMPLIANCE-*`.
