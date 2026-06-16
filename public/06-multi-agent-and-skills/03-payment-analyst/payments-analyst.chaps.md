# payments-analyst · CHAPS reference

> Loaded when **CHAPS** is in scope. Capability + enforceable rules. Cite `CHAPS-*` IDs. Edit in place, keep IDs stable.

## Capability
| Field | Value |
|-------|-------|
| Region | United Kingdom |
| Type | High-value / time-critical credit transfer, real-time gross settlement |
| Currency | **GBP only** |
| Identifiers | Sort code + account number; BIC |
| Message standard | ISO 20022 (`pacs.008`) |
| Settlement | **Same-day, real-time gross**, final & irrevocable |
| Availability | CHAPS business days, 06:00–18:00 UK time |
| Cutoff | Customer payments 17:40, interbank 18:00 (UK time) |

## Rules
- **CHAPS-1** — GBP only; validate sort code + account number (and BIC where used).
- **CHAPS-2** — Same-day settlement; payment is **final and irrevocable** once settled. No reversal — recovery is a new payment / recall request.
- **CHAPS-3** — Enforce the **17:40 customer cutoff**; after cutoff the payment is rejected and must be resubmitted the next business day.
- **CHAPS-4** — Liquidity dependency for settlement; queued/pending payments are handled with operator visibility (`DOWN-R1`).
- **CHAPS-5** — Sanctions screening **before** settlement given finality (`COMPLIANCE-1R`); high-value triggers enhanced AML/reporting scrutiny (`COMPLIANCE-3R/4R`).
- **CHAPS-6** — Typically used for high-value / property / time-critical payments; purpose is captured where required and maker/checker applies (`EXC-R2`).
