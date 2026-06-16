# Feature Specification: Transaction History

**Feature Branch**: `008-transaction-history`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "A list of past transactions performed by the user. Each transaction has creditor name and IBAN, amount, currency and date. There are 20 transactions per page and the user can search by date range, amount range or name."

---

<!-- Architecture Governance Pre-Assessment (Principle VIII)
  Trust Boundaries:
    TB-1: Authenticated user session → Transaction History API
    TB-2: Transaction History API → Core Banking / Transaction DB
  STRIDE:
    - Information Disclosure: IDOR risk (user A accessing user B's transactions) — HIGH
    - Spoofing: Auth token forgery — mitigated by existing JWT validation
    - DoS: Unbounded filter queries degrading DB performance — MEDIUM
  Zero Trust: APPLIES — every request scoped to authenticated user identity; no implicit trust on session
  S-ADR: N/A — read-only feature, no delegated identity or new cross-service auth patterns
  OWASP SAMM: Data classification Level 2 (confidential financial data)
  Memory-safe language: N/A — existing Python 3.12 stack continues
-->

## User Scenarios & Testing *(mandatory)*

### User Story 1 — View Recent Transactions (Priority: P1)

A customer logs into their banking portal and navigates to the Transaction History page to review their most recent outgoing payments. They see a paginated list of transactions, each showing who was paid, the IBAN, the amount and currency, and the date.

**Why this priority**: This is the core value of the feature — without it no other capability exists. Every other story builds on top of this view.

**Independent Test**: Can be fully tested by logging in as a valid user, navigating to the transaction history page, and verifying that the 20 most recent transactions are displayed with the correct fields (creditor name, IBAN, amount, currency, date).

**Acceptance Scenarios**:

1. **Given** a logged-in user with at least one past transaction, **When** they open the Transaction History page, **Then** they see up to 20 transactions ordered by date descending, each showing creditor name, masked IBAN, amount, currency, and transaction date.
2. **Given** a logged-in user with more than 20 transactions, **When** they open the first page, **Then** pagination controls appear showing the current page, total pages, and allow navigation to the next page.
3. **Given** a logged-in user with no past transactions, **When** they open the Transaction History page, **Then** a clear empty-state message is displayed ("No transactions found").
4. **Given** an unauthenticated visitor, **When** they attempt to access the Transaction History page, **Then** they are redirected to the login page.

---

### User Story 2 — Search by Creditor Name (Priority: P2)

A customer wants to find all payments made to a specific merchant or person. They type the creditor's name (or part of it) into the search field and the list updates to show only matching transactions.

**Why this priority**: Name search is the most intuitive way to locate a known payee, covering the majority of "find a specific transaction" use cases.

**Independent Test**: Can be fully tested by entering a partial creditor name in the search field and verifying only transactions whose creditor name contains the search term are displayed, with accurate pagination of results.

**Acceptance Scenarios**:

1. **Given** a user with transactions to multiple creditors, **When** they type a partial creditor name (e.g., "Telef"), **Then** only transactions where the creditor name contains "Telef" (case-insensitive) are shown.
2. **Given** a name search with no matching transactions, **When** the user submits the search, **Then** the empty-state message appears and pagination is hidden.
3. **Given** a name search returning more than 20 results, **When** the results are displayed, **Then** they are paginated with 20 per page.

---

### User Story 3 — Filter by Date Range (Priority: P2)

A customer wants to review all payments made during a specific period (e.g., last month, or Q1 of this year). They set a "from" and "to" date and the list narrows to only transactions within that window.

**Why this priority**: Date-range filtering is essential for account reconciliation and monthly expense review, the most common reason customers browse transaction history.

**Independent Test**: Can be fully tested by setting a start date and end date and verifying only transactions within that inclusive date range are returned.

**Acceptance Scenarios**:

1. **Given** a date range where both dates are provided, **When** the filter is applied, **Then** only transactions with a date on or between the from-date and to-date are shown.
2. **Given** only a "from" date is provided, **When** the filter is applied, **Then** all transactions from that date onward are shown.
3. **Given** only a "to" date is provided, **When** the filter is applied, **Then** all transactions up to and including that date are shown.
4. **Given** a "from" date later than the "to" date, **When** the user submits, **Then** a clear validation error is displayed before any search is performed.

---

### User Story 4 — Filter by Amount Range (Priority: P3)

A customer wants to identify large payments or find a transaction they remember being "around €200". They set a minimum and/or maximum amount and the list filters accordingly.

**Why this priority**: Amount filtering is useful but used less frequently than date or name search; it primarily supports expense analysis and fraud review.

**Independent Test**: Can be fully tested by setting a min and/or max amount and verifying only transactions with amounts within the specified range are displayed.

**Acceptance Scenarios**:

1. **Given** a minimum and maximum amount are set, **When** the filter is applied, **Then** only transactions with amount ≥ min and ≤ max are shown.
2. **Given** only a minimum amount is provided, **When** the filter is applied, **Then** transactions with amount ≥ min are shown.
3. **Given** a negative minimum amount is entered, **When** the user submits, **Then** a validation error is displayed.
4. **Given** amount filters are combined with a name search, **When** the combined filter is applied, **Then** only transactions matching all active filter criteria are shown.

---

### Edge Cases

- What happens when the user clears all filters? → The full transaction list reloads with default pagination.
- What happens if a very broad filter matches thousands of records? → Pagination handles display; total count is shown but capped at 10,000 for performance.
- What happens when the user navigates directly to page 5 and then applies a filter? → The page resets to page 1 of the filtered results.
- What happens if the session expires mid-browsing? → The next request returns an authentication error and the user is redirected to login.
- How are multi-currency amounts handled in amount range filters? → Amount filters apply to the transaction amount in the transaction's own currency; cross-currency comparison is out of scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display a paginated list of the authenticated user's past outgoing transactions.
- **FR-002**: Each transaction entry MUST display: creditor name, masked creditor IBAN (last 4 digits visible, remainder replaced with asterisks), transaction amount, currency code (ISO 4217), and transaction date.
- **FR-003**: The system MUST display exactly 20 transactions per page.
- **FR-004**: The system MUST provide pagination controls: previous page, next page, and current page indicator (e.g., "Page 2 of 15").
- **FR-005**: The system MUST display the total count of transactions matching the current filter state.
- **FR-006**: The system MUST provide a creditor name search field supporting partial, case-insensitive matching.
- **FR-007**: The system MUST provide date range filters with independent "from" and "to" date inputs.
- **FR-008**: The system MUST provide amount range filters with independent minimum and maximum amount inputs.
- **FR-009**: All active filters MUST be combinable simultaneously (name + date range + amount range).
- **FR-010**: When a filter is applied or changed, the results MUST reset to page 1.
- **FR-011**: Active filters MUST persist when the user navigates between pages.
- **FR-012**: The system MUST display a clear empty-state message when no transactions match the current filters.
- **FR-013**: Date inputs MUST validate that "from" date is not later than "to" date before submitting.
- **FR-014**: Amount inputs MUST reject negative values and display a validation error.

### Security & Compliance Requirements *(mandatory for banking systems)*

- **SEC-001**: Every request to the transaction list endpoint MUST be authenticated using a valid JWT; unauthenticated requests MUST be rejected with HTTP 401.
- **SEC-002**: The system MUST ensure that users can only retrieve their own transactions; any attempt to access another user's data MUST be rejected with HTTP 403 (IDOR prevention).
- **SEC-003**: All data MUST be transmitted over TLS 1.2 or higher; plaintext access MUST be refused.
- **SEC-004**: Creditor IBAN MUST be masked in all display surfaces, showing only the last 4 characters (e.g., `****6789`).
- **SEC-005**: All search and filter inputs MUST be validated and sanitised server-side before use in data queries.
- **SEC-006**: Access to transaction history MUST be logged per **DI-004** to support fraud investigation and regulatory audit.

### Data Integrity Requirements *(mandatory for financial features)*

- **DI-001**: Transaction records exposed by this feature are read-only; this feature MUST NOT allow modification or deletion of any transaction record.
- **DI-002**: Transaction amounts MUST be displayed with the correct decimal precision for the transaction currency (e.g., 2 decimal places for EUR, 0 for JPY).
- **DI-003**: The transaction list MUST reflect data no older than 60 seconds from the authoritative source of record.
- **DI-004**: The system MUST maintain an `audit_log` table containing at minimum: `operation_type` (e.g., `TRANSACTION_HISTORY_VIEWED`), `operation_id` (UUID), `initiator` (authenticated user identity), `timestamp` (server-set TIMESTAMPTZ), and `filters_applied` (JSON snapshot of active filters).
- **DI-005**: Each transaction history view event MUST produce exactly one `audit_log` entry written within the same request scope. Requests that cannot write their audit entry MUST fail with an error response.

### Performance Requirements

- **PERF-001**: The default (unfiltered) first page MUST load within 500ms at the 95th percentile.
- **PERF-002**: Filtered search results (date range, name, amount) MUST return within 1 second at the 95th percentile for up to 24 months of transaction history.
- **PERF-003**: Pagination navigation (next/previous page) MUST complete within 500ms at the 95th percentile.
- **PERF-004**: The system MUST support at least 500 concurrent authenticated users browsing transaction history without performance degradation.

### Key Entities *(include if feature involves data)*

- **Transaction**: A completed outgoing payment record. Key attributes: unique identifier, creditor name, creditor IBAN, transaction amount, currency code, transaction date, and originating account reference.
- **TransactionFilter**: The set of search/filter criteria active in a given request. Attributes: creditor name (partial text), date from, date to, amount minimum, amount maximum, page number.
- **AuditEntry**: An immutable record of a transaction history view event. Attributes: operation type, operation ID, initiator identity, timestamp, filters applied.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can locate a specific past transaction by creditor name in under 30 seconds from landing on the transaction history page.
- **SC-002**: 95% of transaction list page loads (first page, unfiltered) complete in under 500ms.
- **SC-003**: 95% of filtered search operations return results in under 1 second for up to 24 months of history.
- **SC-004**: Zero cross-user data leakage incidents — all automated security scans pass with no IDOR findings.
- **SC-005**: 100% of transaction history view events are captured in the audit log (verified by log-vs-request reconciliation).
- **SC-006**: Transaction amounts and IBAN masking display correctly across all supported currencies and account types, with zero display-accuracy defects in acceptance testing.

## Assumptions

- The authenticated user's identity is established by an existing JWT-based authentication system shared with other features (spec 001).
- Transaction data is stored in a core banking database already accessible to the API layer; no new data ingestion pipeline is required.
- "Past transactions" means outgoing debit transactions initiated by the user; incoming credits and internal account transfers are out of scope for this feature version.
- The system will expose only transactions from the past 24 months; older records are archived and out of scope.
- Mobile-native support is out of scope; this feature targets the web banking portal.
- Currency symbol display and locale-specific formatting are handled by the front-end presentation layer, not this feature specification.
- The 20-per-page limit is fixed and not user-configurable in this version.
