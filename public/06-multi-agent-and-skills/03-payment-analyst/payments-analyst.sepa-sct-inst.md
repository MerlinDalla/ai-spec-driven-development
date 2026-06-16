# payments-analyst · SEPA Instant Credit Transfer (SCT Inst) reference

> Loaded when **SEPA SCT Inst** is in scope. Capability + enforceable rules. Cite `SEPA-INST-*` IDs. Edit in place, keep IDs stable.

## Capability
| Field | Value |
|-------|-------|
| Region | EU/EEA + SEPA Inst-reachable PSPs |
| Type | Instant credit transfer (push) |
| Currency | **EUR only** |
| Identifiers | IBAN |
| Message standard | ISO 20022 `pacs.008` (instant variant) |
| Settlement | End-to-end within 10 seconds |
| Availability | **24/7/365** |
| Amount cap | EUR 100,000 per transaction |

## Rules
- **SEPA-INST-1** — Currency MUST be EUR; beneficiary IBAN validated (structure/country/check digits).
- **SEPA-INST-2** — Both PSPs must be **reachable for SCT Inst** specifically (Inst reachability ≠ SCT reachability). Verify before routing.
- **SEPA-INST-3** — Enforce the **EUR 100,000 per-transaction cap**. Over-cap instructions are rejected; the operator may resubmit as a standard SCT.
- **SEPA-INST-4** — **Timeout handling is mandatory.** If confirmation isn't received within 10 seconds the payment is treated as rejected/failed (not pending); the final state is unambiguous and the customer/operator is notified.
- **SEPA-INST-5** — Service runs **24/7** — sanctions screening (`COMPLIANCE-1R`) operates in real time without a manual-queue bottleneck that breaks the time limit. A hit that cannot be cleared within the time limit results in rejection.
- **SEPA-INST-6** — Instant finality: once accepted, funds are **irrevocable**. Recovery is only via recall request, not reversal. The recall flow is specified and is not guaranteed.
- **SEPA-INST-7** — Idempotency/duplicate detection is critical given retries on uncertain outcomes (`DOWN-R2`); a retry must never cause a second credit.
