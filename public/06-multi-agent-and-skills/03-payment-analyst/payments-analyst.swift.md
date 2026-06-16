# payments-analyst · SWIFT cross-border reference

> Loaded when **SWIFT cross-border** payments are in scope. Capability + enforceable rules. Cite `SWIFT-*` IDs. Edit in place, keep IDs stable.

## Capability
| Field | Value |
|-------|-------|
| Region | Global |
| Type | Cross-border credit transfer |
| Currency | **Multi-currency** (per `payments-analyst.currencies.md`) |
| Identifiers | BIC; IBAN or local account number; correspondent details |
| Message standard | ISO 20022 MX (`pacs.008`/`pacs.009`); MT legacy where still used; gpi tracking |
| Settlement | Correspondent / nostro-vostro dependent; not real-time |
| Cutoff | Per currency at the correspondent: USD 17:00 ET, EUR 16:00 CET, GBP 16:00 GMT |

## Rules
- **SWIFT-1** — Capture full **correspondent banking chain**: debtor agent, creditor agent, and any intermediary agents. Validate BICs; where no direct relationship exists, route via the configured correspondent.
- **SWIFT-2** — **Charge bearer (OUR / SHA / BEN)** is mandatory and drives fee deduction and credited amount (`CCY-6R`). Correspondent/intermediary charges are handled and disclosed per the charge-bearer option.
- **SWIFT-3** — Cross-currency legs require FX handling per `CCY-5R` (rate source, type, timestamp, 60-second tolerance, stale-rate routing to FX-exception queue).
- **SWIFT-4** — **Nostro/vostro reconciliation** is mandatory; expected debit/credit confirmations (camt/MT940/950) are matched and breaks routed to the reconciliation queue (`DOWN-R1`).
- **SWIFT-5** — Sanctions screening on all parties incl. intermediaries and narrative (`COMPLIANCE-1R`); cross-border raises higher AML/reporting exposure (`COMPLIANCE-3R/4R`).
- **SWIFT-6** — Support **gpi** tracking (UETR) for status/traceability; the gpi status states are surfaced to operators.
- **SWIFT-7** — **Returns / recalls / cancellation requests** (incl. gpi stop-and-recall) are specified with their non-guaranteed nature, time windows, and approvals (`EXC-R1/R2`).
- **SWIFT-8** — Validate per-currency value date and cutoff; non-business days per the relevant currency calendar (`DATE-R1/R2`).
- **SWIFT-9** — When migrating MT↔MX, flag field-mapping and truncation risks (structured vs unstructured data).
