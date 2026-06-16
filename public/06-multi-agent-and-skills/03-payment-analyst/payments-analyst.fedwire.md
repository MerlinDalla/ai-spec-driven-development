# payments-analyst · Fedwire reference

> Loaded when **Fedwire** is in scope. Capability + enforceable rules. Cite `FEDWIRE-*` IDs. Edit in place, keep IDs stable.

## Capability
| Field | Value |
|-------|-------|
| Region | United States |
| Type | High-value / urgent credit transfer, real-time gross settlement |
| Currency | **USD only** |
| Identifiers | ABA routing number + account number; BIC for correspondents |
| Message standard | Fedwire format; ISO 20022 migration |
| Settlement | **Real-time gross**, final & irrevocable |
| Availability | Fedwire business days |
| Cutoff | Customer payments 18:00 ET; system closing 19:00 ET |

## Rules
- **FEDWIRE-1** — USD only; validate ABA routing number + account number.
- **FEDWIRE-2** — **Gross, same-day settlement** — final and irrevocable once settled. No reversal; recovery is a new payment / recall request.
- **FEDWIRE-3** — Enforce the **18:00 ET customer cutoff**; after cutoff the payment is rejected and must be resubmitted the next business day.
- **FEDWIRE-4** — Liquidity dependency; queued/pending payments are handled with operator visibility (`DOWN-R1`).
- **FEDWIRE-5** — OFAC sanctions screening **before** settlement given finality (`COMPLIANCE-1R`); high-value triggers enhanced AML/reporting (`COMPLIANCE-3R/4R`).
- **FEDWIRE-6** — When migrating to ISO 20022, flag field-mapping/truncation risks vs legacy format.
- **FEDWIRE-7** — Capture originator-to-beneficiary info and any required regulatory/travel-rule data.
