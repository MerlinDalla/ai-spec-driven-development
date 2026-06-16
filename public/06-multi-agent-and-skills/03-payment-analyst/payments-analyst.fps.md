# payments-analyst · Faster Payments (FPS) reference

> Loaded when **UK Faster Payments** is in scope. Capability + enforceable rules. Cite `FPS-*` IDs. Edit in place, keep IDs stable.

## Capability
| Field | Value |
|-------|-------|
| Region | United Kingdom |
| Type | Instant / near-real-time credit transfer |
| Currency | **GBP only** |
| Identifiers | Sort code + account number |
| Message standard | ISO 20022 |
| Settlement | Near-real-time |
| Availability | **24/7** |
| Amount cap | GBP 1,000,000 per transaction |

## Rules
- **FPS-1** — GBP only; validate sort code + account number.
- **FPS-2** — Enforce the **GBP 1,000,000 per-transaction limit**; over-limit payments are rejected and may be routed to CHAPS.
- **FPS-3** — **24/7 near-real-time** — real-time sanctions screening required without breaking the time expectation; a hit holds the payment for review (`COMPLIANCE-1R`).
- **FPS-4** — Define **timeout / uncertain-outcome** handling and the unambiguous final state; notify customer/operator.
- **FPS-5** — Idempotency / duplicate detection on retries (`DOWN-R2`); a retry must never double-credit.
- **FPS-6** — **Confirmation of Payee (CoP)** name-matching is in scope for GBP push payments; match / close-match / no-match outcomes drive the user warning flow before submission.
- **FPS-7** — Returns are via a new payment, not reversal; unpaid/return reason handling is specified.
