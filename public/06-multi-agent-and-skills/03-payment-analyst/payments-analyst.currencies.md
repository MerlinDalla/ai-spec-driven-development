# payments-analyst · currencies reference

> Loaded on **every** analysis. The supported-currency list and the rules for amount precision, FX, and rounding. Cite `CCY-*` IDs in findings. `Minor units` = decimal places (ISO 4217) and is critical for amount handling, validation, and rounding. Edit the table to change the supported set; keep rule IDs stable.

## Supported currencies
| ID | Currency | Code | Minor units | Notes |
|----|----------|------|-------------|-------|
| CCY-1 | Euro | EUR | 2 | SEPA & TARGET2 base currency |
| CCY-2 | Pound sterling | GBP | 2 | CHAPS / FPS / Bacs |
| CCY-3 | US dollar | USD | 2 | ACH / Fedwire / SWIFT |
| CCY-4 | Swiss franc | CHF | 2 | |
| CCY-5 | Japanese yen | JPY | 0 | **No minor units** — amounts are whole numbers |
| CCY-6 | Polish złoty | PLN | 2 | |
| CCY-7 | Kuwaiti dinar | KWD | 3 | **3-decimal currency** — validate precision handling |

*Unsupported / restricted currencies:* reject any currency not in the table above. Additionally reject currencies of sanctioned/embargoed jurisdictions per the bank's sanctions policy.

## Rules
- **CCY-1R** — Transaction currency MUST be in the supported list above. Reject unsupported currencies with a specific reason.
- **CCY-2R** — Amounts MUST respect the currency's minor units. Reject sub-unit precision (e.g., 3 decimals on USD, any decimals on JPY, >3 on KWD).
- **CCY-3R** — Currency must be eligible for the chosen scheme (see scheme files, e.g. SEPA = EUR only). Currency/scheme mismatch is a hard validation failure.
- **CCY-4R** — Rounding mode for FX conversion and fee calculation is **half-up to the target currency's minor units**. Totals must reconcile to the minor unit; no residual rounding leakage.
- **CCY-5R** — Cross-currency payments require an FX rate **source, type (spot/contracted), timestamp, and tolerance**. Rate validity is 60 seconds for spot quotes; a stale or missing rate routes the payment to the FX-exception queue rather than settling.
- **CCY-6R** — Charge bearer (**OUR / SHA / BEN**) is captured for cross-border payments and drives who bears fees and how the credited amount is computed (see `payments-analyst.swift.md`).
- **CCY-7R** — Store and display amounts with the currency code; never assume a default currency. Mixed-currency totals must not be summed without conversion.
