# payments-analyst · TARGET2 / T2 (RTGS) reference

> Loaded when **TARGET2 / T2 RTGS** is in scope. Capability + enforceable rules. Cite `T2-*` IDs. Edit in place, keep IDs stable.

## Capability
| Field | Value |
|-------|-------|
| Region | Eurosystem |
| Type | High-value / urgent credit transfer, real-time gross settlement |
| Currency | **EUR only** |
| Identifiers | BIC; IBAN |
| Message standard | ISO 20022 (`pacs.008`, `pacs.009`, camt reporting) |
| Settlement | **Real-time gross**, central-bank money, settlement-finality |
| Availability | TARGET business days; intraday windows |
| Cutoff | Customer payments (`pacs.008`) 17:00 CET; interbank (`pacs.009`) 18:00 CET |

## Rules
- **T2-1** — EUR only; high-value/urgent. Validate BIC and IBAN.
- **T2-2** — **Gross settlement** — each payment settles individually and is **final and irrevocable** upon settlement. No netting; no reversal — recovery is a new payment.
- **T2-3** — **Liquidity dependency:** a payment settles only if the RTGS account has sufficient liquidity. Insufficient-liquidity payments are queued with prioritisation/reservation; the operator has a view of queued/pending payments.
- **T2-4** — Enforce **intraday cutoffs**: customer payments after 17:00 CET and interbank after 18:00 CET are rejected and must be resubmitted the next business day.
- **T2-5** — Payment priority (normal / urgent / highly-urgent) must be capturable and drive queue ordering.
- **T2-6** — Sanctions screening before submission (`COMPLIANCE-1R`); given finality, a hit must be resolved **before** settlement, never after.
- **T2-7** — Reconciliation against camt statements and the RTGS account is mandatory (`DOWN-R1`); the break-handling flow is defined.
