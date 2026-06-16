# Feature Specification: Currency Conversion & Cross-Currency Transfer

**Feature Branch**: `002-currency-fx-transfer`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "Currency conversion table and an ability to transfer money between different-currency accounts"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Live Exchange Rates (Priority: P1)

A bank customer wants to check the current exchange rates before deciding to transfer money internationally. They open the currency conversion table, which shows a list of supported currencies and their exchange rates relative to a base currency. The customer can see rates at a glance and optionally enter an amount to preview the converted value.

**Why this priority**: Viewing rates is a prerequisite for any cross-currency decision and delivers standalone value even without executing a transfer. It builds user confidence before committing funds.

**Independent Test**: Can be fully tested by navigating to the exchange rate table, verifying rates are displayed, and entering an amount to see a preview — delivers immediate informational value with no transfer needed.

**Acceptance Scenarios**:

1. **Given** a customer is authenticated, **When** they navigate to the currency conversion section, **Then** they see a table listing all supported currency pairs with current buy/sell rates and a "last updated" timestamp.
2. **Given** the conversion table is displayed, **When** the customer enters an amount in a source currency, **Then** the equivalent amount in the target currency is shown instantly using the current rate, along with any applicable fees.
3. **Given** exchange rates have not been refreshed in over 60 minutes, **When** a customer views the table, **Then** rates are automatically refreshed before display and the timestamp reflects the new retrieval time.

---

### User Story 2 - Transfer Money Between Own Accounts in Different Currencies (Priority: P2)

A customer holds accounts in two different currencies (e.g., EUR and USD) and wants to transfer funds from one to the other. They initiate a cross-currency transfer, review the exchange rate and fee summary, confirm the transaction, and both account balances update accordingly.

**Why this priority**: This is the core transactional feature. It depends on rates being available (P1) but delivers the primary financial value of the feature.

**Independent Test**: Can be fully tested end-to-end by initiating a transfer between two test accounts in different currencies, confirming it, and verifying both balances and audit records updated correctly.

**Acceptance Scenarios**:

1. **Given** a customer has a EUR account with sufficient balance and a USD account, **When** they initiate a transfer of 100 EUR to their USD account, **Then** they are shown the exact USD amount they will receive, the exchange rate applied, and any fees before confirmation.
2. **Given** the customer reviews and confirms the cross-currency transfer, **When** the transaction is processed, **Then** the source account is debited the sent amount plus fees, the destination account is credited the converted amount, and both changes are atomic (either both succeed or neither applies).
3. **Given** a customer initiates a transfer, **When** the source account has insufficient funds to cover the transfer amount plus fees, **Then** the transfer is rejected with a clear message stating the shortfall and no balances are changed.
4. **Given** a completed cross-currency transfer, **When** the customer reviews their transaction history, **Then** the transfer appears with: source amount, source currency, destination amount, destination currency, exchange rate used, fees charged, and timestamp.

---

### User Story 3 - Transfer Money to Another Customer's Account in a Different Currency (Priority: P3)

A customer wants to send money to another account holder whose account is denominated in a different currency. They look up the recipient, review the conversion details, and execute the transfer.

**Why this priority**: Extends cross-currency capability to third-party transfers. Builds on P2 mechanics but introduces recipient lookup and additional compliance checks, making it more complex.

**Independent Test**: Can be tested by initiating a cross-currency transfer to a different account holder using test accounts and verifying conversion, debit, credit, and audit trail are all correct.

**Acceptance Scenarios**:

1. **Given** a customer wants to send funds to a recipient with a different-currency account, **When** they enter the recipient's account identifier and the amount to send, **Then** they see the recipient's account currency, the converted amount the recipient will receive, the applicable rate, and fees.
2. **Given** the customer confirms a third-party cross-currency transfer, **When** it is processed, **Then** the sender's account is debited and the recipient's account is credited atomically, with an in-app notification delivered to both parties within the banking platform.

---

### Edge Cases

- What happens when the exchange rate service is unavailable? — Transfer initiation is blocked; user sees a clear error; no funds are moved.
- What happens when exchange rates are available but stale (older than the configured maximum age)? — Rates are displayed in read-only mode with a visible stale warning; transfer initiation is blocked until fresh rates are obtained.
- What happens if the exchange rate changes significantly between preview and confirmation? — The system re-validates the rate at confirmation time; if the rate deviated by more than a configurable threshold (default: 1%), the user is shown the updated rate and must re-confirm.
- What happens when the source account balance becomes insufficient after the rate update? — Transfer is rejected with a message explaining the insufficiency.
- How does the system handle rounding in currency conversions? — Rounding follows standard banking convention (half-up) and is done at the final conversion step; the rounding difference is absorbed, not charged to the customer.
- What happens if two concurrent transfers from the same account would together exhaust the balance? — Transfers are serialised via pessimistic account-level locking; the second transfer re-checks balance after the first completes and is rejected with an insufficient-funds error if balance is inadequate.
- What happens if a transfer is submitted twice (duplicate)? — Idempotency key on each transfer request prevents double-processing; duplicate submissions return the result of the original request.

## Clarifications

### Session 2026-06-15

- Q: Are fees charged on top of the source amount or deducted from it? → A: Fee split — sender pays a sending fee deducted from/added to their account; recipient pays a receiving fee deducted from the converted amount credited to their account.
- Q: What states should a cross-currency transfer go through? → A: PENDING → PROCESSING → COMPLETED / FAILED (4-state lifecycle).
- Q: What should the system do when exchange rates are available but stale beyond the refresh interval? → A: Block transfer initiation and display a stale-rate error; rate viewing is still allowed.
- Q: How should transfer notifications be delivered to sender and recipient? → A: In-app notification only (within the banking platform); no external channels (email, SMS) in scope for v1.
- Q: How should the system handle concurrent transfers that together would exceed the account balance? → A: Serialise via pessimistic account lock — the second transfer waits, then re-checks balance and fails with an insufficient-funds error if the balance is no longer adequate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a currency conversion table showing all supported currency pairs with current exchange rates (buy and sell) and a "last updated" timestamp.
- **FR-002**: System MUST allow users to enter an amount in a source currency and instantly preview the equivalent amount in a selected target currency using the current rate.
- **FR-003**: System MUST refresh exchange rates automatically at a configurable interval (default: 60 minutes) and on-demand before displaying the rate table. If rates cannot be refreshed and the last known rates exceed the configured maximum age, the system MUST mark rates as stale.
- **FR-003a**: When rates are stale, the system MUST display the rate table in a read-only stale state (with a visible stale warning and last-updated timestamp) and MUST block all transfer initiation until fresh rates are obtained.
- **FR-004**: System MUST allow authenticated customers to initiate a cross-currency transfer between any two accounts (own or third-party) where the accounts are in different currencies.
- **FR-005**: System MUST display a pre-confirmation summary showing: source amount, source currency, sending fee (charged to sender on top of source amount), gross converted amount, receiving fee (deducted from the amount credited to recipient), net amount received by recipient, exchange rate applied, and total cost to sender.
- **FR-006**: System MUST re-validate the exchange rate at the moment of confirmation and alert the user if the rate has deviated by more than the configured threshold since the preview.
- **FR-007**: System MUST execute cross-currency transfers atomically — the source account debit (transfer amount + sending fee) and destination account credit (converted amount minus receiving fee) MUST either both succeed or both be rolled back.
- **FR-008**: System MUST reject a transfer if the source account balance is insufficient to cover the transfer amount plus the sending fee, and MUST communicate the shortfall clearly.
- **FR-009**: System MUST record every cross-currency transfer in the transaction history of both the source and destination accounts, including: source amount, source currency, sending fee, converted amount, destination currency, receiving fee, net amount credited, exchange rate used, transfer status, and timestamp.
- **FR-010**: System MUST guarantee idempotency for transfer submissions — resubmitting the same transfer request MUST NOT result in duplicate debits or credits.
- **FR-011**: System MUST support a configurable list of allowed currency pairs; currency pairs not in the list MUST NOT be available for selection.
- **FR-012**: System MUST expose the current status of a transfer (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) to the customer; a `FAILED` transfer MUST display the reason for failure and confirm no funds were moved.
- **FR-013**: Upon completion of a third-party cross-currency transfer, the system MUST deliver an in-app notification to both the sender and recipient within the banking platform; external notification channels (email, SMS) are out of scope for v1.
- **FR-014**: In-app notifications MUST include: transfer direction (sent/received), source amount and currency, net amount credited and currency, and a link to the transfer detail record.

### Security & Compliance Requirements *(mandatory for banking systems)*

- **SEC-001**: System MUST authenticate and authorize all requests; only the account holder (or authorized agent) may initiate transfers from an account.
- **SEC-002**: System MUST enforce transfer limits per transaction and per day, configurable by customer tier, to comply with AML controls.
- **SEC-003**: System MUST log all transfer initiation, confirmation, and rejection events with authenticated user identity, timestamp, and outcome.
- **SEC-004**: System MUST apply AML/KYC screening checks before processing third-party cross-currency transfers above a configurable threshold.
- **SEC-005**: All data in transit MUST be encrypted; account numbers and balances MUST be masked in logs beyond the minimum required for audit traceability.
- **SEC-006**: System MUST comply with applicable regulatory requirements for cross-currency and cross-border payments (e.g., SWIFT/SEPA reporting if applicable).

### Data Integrity Requirements *(mandatory for financial features)*

- **DI-001**: All balance updates (debit and credit) MUST be performed within a single ACID transaction; partial updates are not permitted. Concurrent transfers from the same account MUST be serialised via pessimistic account-level locking — a second transfer MUST wait for the first to complete, then re-validate balance before proceeding.
- **DI-002**: All monetary amounts and exchange rates MUST be stored and calculated using decimal types with sufficient precision (minimum 6 decimal places for rates; 2 decimal places for displayed amounts in standard currencies).
- **DI-003**: System MUST validate that the source account has sufficient balance before initiating any debit operation.
- **DI-004**: System MUST maintain an `audit_log` table containing at minimum: `operation_type` (controlled enum), `operation_id` (UUID), `initiator` (authenticated identity), `timestamp` (server-set TIMESTAMPTZ).
- **DI-005**: Every state-changing operation MUST produce exactly one `audit_log` entry written within the same ACID transaction. Operations that cannot write their audit entry MUST be rolled back. Read-only operations (queries, health checks) are exempt.
- **DI-006**: Exchange rates used in completed transactions MUST be stored immutably alongside the transaction record for regulatory and dispute purposes.

### Performance Requirements

**Measurement baseline**: All p95 latency targets in PERF-001 through PERF-004 apply to server-side processing time measured at the service boundary (excluding client-side rendering and network transit), sampled over a 5-minute rolling window in a staging environment sized equivalently to production. PERF-005 defines a client-side timeout constraint rather than a p95 latency target and is not subject to the rolling-window measurement methodology. "Normal load" is defined as up to 500 concurrent authenticated sessions. These targets are intentionally aligned with the banking performance standards in the project constitution (Principle VI: <500ms p95 for reads, <2s p95 for writes).

- **PERF-001**: Exchange rate table retrieval and preview calculations MUST complete in under 500ms (p95) at the service boundary under normal load (up to 500 concurrent sessions). The error rate for this operation MUST NOT exceed 0.1% under normal load.
- **PERF-002**: Transfer initiation and transfer confirmation operations MUST each individually complete in under 2 seconds (p95) at the service boundary under normal load. The system MUST support a sustained throughput of at least 50 combined transfer operations (initiations + confirmations) per second. The error rate for these operations MUST NOT exceed 0.5% under normal load.
- **PERF-003**: A "concurrent transfer session" is defined as an authenticated user session with at least one transfer in `PENDING` or `PROCESSING` state. The system MUST support at least 500 such concurrent sessions simultaneously. At peak load (500 concurrent sessions), p95 latency for PERF-001 and PERF-002 operations MUST NOT exceed 150% of their respective baseline targets (≤750ms and ≤3s respectively). For load exceeding 500 concurrent sessions, the system MUST reject new transfer initiations with an explicit capacity error rather than allowing unbounded latency growth; exchange rate table reads MAY continue to be served.
- **PERF-004**: Exchange rate refresh operations (scheduled and on-demand, per FR-003) MUST complete within 10 seconds (p95), measured from the moment the refresh is triggered (scheduled timer fires or on-demand request arrives at the service) to the moment updated rates are committed to the DB snapshot and available for read-serving. The error rate for refresh operations MUST NOT exceed 1% under normal load. Refresh operations MUST execute on a separate processing path and MUST NOT block or degrade user-facing operations covered by PERF-001 or PERF-002. During an ongoing refresh, the most recently cached rates MUST remain available for read-only display as defined in FR-003a. If a scheduled refresh and an on-demand refresh are triggered concurrently, they MUST be deduplicated into a single in-flight refresh operation; only one provider call MUST be made.
- **PERF-005**: All outbound calls to the external FX rate provider MUST have a per-request client-side timeout of 5 seconds (configurable via the `FX_PROVIDER_TIMEOUT_SECONDS` environment variable). Before falling back to cached rates, the system MUST retry the provider up to 2 times with exponential backoff (initial delay: 500ms, factor: 2×). If the provider does not respond within this timeout after all retries, the system MUST NOT propagate the delay into user-facing operations; it MUST serve the most recently cached rates (if within the configured maximum age) within the PERF-001 latency budget (≤500ms p95 at the service boundary), or activate the stale-rate behaviour defined in FR-003a if no fresh-enough cached rates are available.
- **PERF-006**: Prior to any production deployment, load testing MUST be executed simulating 500 concurrent transfer sessions sustained for a minimum of 10 minutes, preceded by a 2-minute linear ramp-up from 0 to 500 concurrent sessions. The staging environment used MUST meet the following minimum criteria to qualify as production-equivalent: (a) compute capacity matching the production deployment (same CPU and memory tier); (b) PostgreSQL database with a minimum of 10,000 representative transfer records; (c) network latency between service and database within 10% of the production baseline. The deployment MUST be blocked unless all of the following are validated: all p95 latency targets (PERF-001 through PERF-004) and their error-rate thresholds; the graceful-degradation behaviour at peak load (PERF-003), including explicit verification that new transfer initiations beyond 500 concurrent sessions are rejected with an HTTP 503 capacity error; and continued availability of exchange rate table reads under peak load. This gate MUST be enforced by an automated CI/CD pipeline step that parses load test results and fails the pipeline if any criterion is not met; manual override requires written approval from the technical lead with documented justification.

### Key Entities *(include if feature involves data)*

- **ExchangeRate**: Represents the rate between a source and target currency; includes buy rate, sell rate, effective timestamp, and source (rate provider).
- **CurrencyPair**: A configured, supported pairing of two currencies (e.g., EUR/USD); drives what options are available in the UI and API.
- **CrossCurrencyTransfer**: A financial transfer between two accounts in different currencies; records source account, destination account, source amount, destination amount, sending fee, receiving fee, rate applied, status (`PENDING` → `PROCESSING` → `COMPLETED` / `FAILED`), and idempotency key. A transfer in `FAILED` state MUST have no net effect on either account balance.
- **Account**: An existing entity representing a customer's bank account with a denominated currency and current balance.
- **Fee**: The charge applied to a cross-currency transfer; split between a sending fee (charged to the sender, added on top of the source amount) and a receiving fee (deducted from the converted amount before crediting the recipient); may be a fixed amount, a percentage of the transfer, or a combination; both fees stored per-transaction.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Customers can view the full exchange rate table and preview a conversion within 3 seconds of requesting the page (end-to-end, user-perceived time, including network transit and any on-demand rate refresh). This 3-second end-to-end budget encompasses the server-side processing time defined in PERF-001 (≤500ms) plus expected network latency and client rendering overhead; the two targets are compatible and non-conflicting.
- **SC-002**: 95% of cross-currency transfer confirmations complete successfully (without errors) within 2 seconds under normal operating conditions.
- **SC-003**: Zero instances of partial transfers — every completed transfer has matching debit and credit records with no orphaned transactions in any monitoring period.
- **SC-004**: 100% of transfer operations (initiated, confirmed, rejected) have a corresponding audit log entry; auditors can reconstruct the full history of any transfer from the audit log alone.
- **SC-005**: Rate deviation alerts are presented to customers within 1 second of a rate change exceeding the threshold at confirmation time, preventing uninformed acceptance of unfavorable rates.
- **SC-006**: Duplicate transfer submissions result in a returned idempotent response with no duplicate financial impact in 100% of cases.

## Assumptions

- The existing authentication and account management system is already in place and will be reused; this feature integrates with it rather than replacing it.
- Exchange rates are sourced from an external rate provider (e.g., an internal treasury feed or a third-party FX data service); this feature consumes rates via an agreed internal interface and does not manage the provider relationship.
- Fee structures are pre-configured by the bank's operations team; the system applies them automatically but does not provide a UI for fee management within this feature's scope.
- Mobile support is in scope to the same degree as the existing fund transfer feature; no new mobile-specific UI is required beyond responsive design.
- Third-party cross-currency transfers (P3) assume the recipient's account is within the same banking system; international wire transfers to external banks are out of scope for this version.
- AML/KYC thresholds and transfer limits will be configured by the compliance team before go-live; the system MUST enforce whatever values are configured.
- Currency rounding follows the ISO 4217 standard for each currency's minor unit (e.g., 2 decimal places for EUR/USD, 0 for JPY).
