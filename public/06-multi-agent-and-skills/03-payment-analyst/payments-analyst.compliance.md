# payments-analyst · compliance reference

> Loaded on **every** analysis. Sanctions screening, AML, and regulatory-reporting rules that apply across schemes. Cite `COMPLIANCE-*` IDs. The analyst **flags** obligations; it never interprets law — interpretation is deferred to the compliance team. Edit in place; keep IDs stable.

## Rules
- **COMPLIANCE-1R** — Every in-scope payment is screened against sanctions / watchlists **before release** (debtor, creditor, agents, and narrative where required). The flow is hold → review → block/release; only a Compliance Officer role may act on a hit, under four-eyes approval.
- **COMPLIANCE-2R** — A screening hit places the payment in a **dedicated sanctions-exception queue**; release requires four-eyes approval and is fully audit-logged (who/what/when/why).
- **COMPLIANCE-3R** — AML monitoring triggers (single transaction ≥ EUR 15,000 equivalent, structuring patterns, high-risk jurisdictions/currencies) raise an alert. AML decisioning is performed by the bank's transaction-monitoring system; this feature raises the alert, routes it to the AML queue, and hands off to SAR/STR reporting — it does not itself decide the AML outcome.
- **COMPLIANCE-4R** — Regulatory reporting obligations (PSD2, large-value / cross-border reporting, scheme-specific) are **identified per feature** and emitted to the regulatory-reporting system; cross-border payments ≥ EUR 12,500 raise the balance-of-payments reporting obligation.
- **COMPLIANCE-5R** — Maintain an immutable, tamper-evident **audit trail** of screening decisions, overrides, and reporting events, retained for 7 years and available for regulator inspection.
- **COMPLIANCE-6R** — PSD2 SCA / strong authentication implications for the initiating channel are flagged where applicable.
- **COMPLIANCE-7R** — Data privacy (GDPR): payment data exposure, retention, and cross-border transfer are flagged; sensitive data minimized in logs and UI (link to security rules).
- **COMPLIANCE-8R** — *Never interpret a regulation or legal obligation.* State the obligation and the trigger, then explicitly defer the interpretation/decision to the compliance team.
