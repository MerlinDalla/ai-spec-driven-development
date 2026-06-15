# Feature Specification: Fund Transfer Service

**Feature Branch**: `001-fund-transfer-service`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "Create a backend for a new Fund Transfer service. It should provide a simple CRUD for creating a new account with starting balance, retrieving an account balance, and transferring funds between accounts. Each account has: number, currency, balance, owner"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a New Account (Priority: P1)

A customer or system operator creates a new account by providing the owner identity,
desired currency, and an opening balance. The system assigns a unique account number
and persists the account so it can be used immediately for balance queries and transfers.

**Why this priority**: Without account creation, no other operation is possible. This is
the foundational building block for the entire service.

**Independent Test**: Can be fully tested by submitting a valid account creation request
and verifying that the returned account number is unique and the stored balance matches
the opening amount.

**Acceptance Scenarios**:

1. **Given** valid owner information, a supported currency, and a non-negative opening
   balance, **When** a create-account request is submitted, **Then** a new account is
   created with a unique account number, the specified currency, and the exact opening
   balance — and the account is immediately queryable.

2. **Given** a request with a negative opening balance, **When** the create-account
   request is submitted, **Then** the system rejects the request with a clear validation
   error and no account is created.

3. **Given** a request missing required fields (owner or currency), **When** the
   create-account request is submitted, **Then** the system returns a descriptive
   validation error for each missing field.

---

### User Story 2 - Retrieve Account Balance (Priority: P1)

An authorized caller retrieves the current balance and details of an account by its
account number. The system returns the latest confirmed balance and account metadata.

**Why this priority**: Balance retrieval is the core read operation; it is needed by
clients before any transfer and is the primary way account state is observed.

**Independent Test**: Can be fully tested by creating an account and immediately
querying it — the returned balance must exactly match the opening balance.

**Acceptance Scenarios**:

1. **Given** an existing account number, **When** a balance retrieval request is
   submitted, **Then** the system returns the account number, owner, currency, and
   current balance accurately.

2. **Given** a non-existent account number, **When** a balance retrieval request is
   submitted, **Then** the system returns a not-found error with no partial data.

3. **Given** an account that has had transfers applied, **When** a balance retrieval
   request is submitted, **Then** the balance reflects all completed transfers exactly.

---

### User Story 3 - Transfer Funds Between Accounts (Priority: P1)

An authorized caller initiates a transfer of a specified amount from one account to
another. The system debits the source account and credits the destination account
atomically, ensuring no money is created or destroyed. A record of the transfer is
retained for audit purposes.

**Why this priority**: Fund transfer is the core business operation of the service;
it is the primary differentiating capability.

**Independent Test**: Can be fully tested end-to-end by creating two accounts,
transferring an amount, and verifying that the source balance decreased and the
destination balance increased by exactly the transfer amount, with the total
combined balance unchanged.

**Acceptance Scenarios**:

1. **Given** two accounts in the same currency with sufficient funds in the source
   account, **When** a transfer request is submitted with a valid positive amount,
   **Then** the source account balance decreases by exactly the transfer amount,
   the destination account balance increases by exactly the transfer amount, and
   the operation is recorded in the audit log.

2. **Given** a source account with insufficient funds, **When** a transfer is
   requested for an amount exceeding the available balance, **Then** the system
   rejects the transfer, both balances remain unchanged, and an appropriate error
   is returned.

3. **Given** a transfer request with a non-positive amount (zero or negative),
   **When** the request is submitted, **Then** the system rejects it with a
   validation error and no balances are modified.

4. **Given** a transfer request referencing a non-existent source or destination
   account, **When** the request is submitted, **Then** the system returns a
   not-found error and no state changes occur.

5. **Given** two identical concurrent transfer requests (same accounts, amount,
   and idempotency key), **When** both are submitted simultaneously, **Then**
   exactly one transfer is executed and the duplicate is safely rejected.

---

### User Story 4 - Delete an Account (Priority: P2)

An authorized operator closes an account, removing it from active use. The account
must have a zero balance before deletion is permitted, ensuring no funds are lost.

**Why this priority**: Completing full CRUD coverage is required; however, account
closure is lower risk because it is a privileged, infrequent operation.

**Independent Test**: Can be fully tested by creating an account, draining its
balance via a transfer, and then deleting it — confirming that subsequent balance
queries return not-found.

**Acceptance Scenarios**:

1. **Given** an account with a zero balance, **When** a delete request is
   submitted, **Then** the account is closed and no longer retrievable.

2. **Given** an account with a non-zero balance, **When** a delete request is
   submitted, **Then** the system rejects the request and the account remains active.

3. **Given** a non-existent account number, **When** a delete request is submitted,
   **Then** the system returns a not-found error.

---

### Edge Cases

- What happens when two concurrent transfers both attempt to debit the same source
  account simultaneously and only one can succeed?
- How does the system behave when the same create-account or transfer request is
  retried multiple times (idempotency)?
- What is the maximum allowed transfer amount? The service enforces a configurable
  per-currency maximum transfer limit (e.g. 1,000,000 EUR per single transfer).
  Requests exceeding the limit are rejected with a clear limit-exceeded error.
- Can an account be queried or transferred from during a deletion in progress?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow creation of an account with a unique account number,
  an owner identifier, a currency code, and a non-negative opening balance.
- **FR-002**: System MUST guarantee that every account number is globally unique.
- **FR-003**: System MUST allow retrieval of an account's number, owner, currency,
  and current balance by account number.
- **FR-004**: System MUST allow transfer of funds between two existing accounts,
  debiting the source and crediting the destination atomically.
- **FR-005**: System MUST reject transfers when the source account has insufficient
  funds to cover the requested amount.
- **FR-006**: System MUST reject transfer amounts that are zero or negative.
- **FR-007**: System MUST allow deletion of an account only when its balance is zero.
- **FR-008**: System MUST return descriptive, structured error responses for all
  invalid operations (missing fields, not-found, insufficient funds, etc.).
- **FR-009**: System MUST support idempotent transfer requests to prevent duplicate
  fund movements on retry.
- **FR-010**: System MUST record an audit entry for every transfer, capturing source
  account, destination account, amount, currency, timestamp, and outcome.
- **FR-011**: System MUST enforce a configurable maximum transfer amount per currency.
  Transfers exceeding the configured limit MUST be rejected with a limit-exceeded error.
- **FR-012**: System MUST support transfers between accounts in different currencies
  using static exchange rates defined in service configuration. The applied rate and
  converted amount MUST be included in the transfer record and audit log.

### Security & Compliance Requirements *(mandatory for banking systems)*

- **SEC-001**: System MUST authenticate all API requests; unauthenticated requests
  MUST be rejected.
- **SEC-002**: System MUST authorize callers so that account data is accessible only
  to the account owner or privileged operators.
- **SEC-003**: System MUST encrypt account data (balance, owner identity) at rest
  and in transit.
- **SEC-004**: System MUST log all write operations (create, transfer, delete) with
  caller identity, timestamp, and outcome for audit compliance.
- **SEC-005**: System MUST comply with applicable data-privacy regulations (GDPR)
  for owner personal data.
- **SEC-006**: System MUST NOT expose internal error details (stack traces, query
  details) in API responses.

### Data Integrity Requirements *(mandatory for financial features)*

- **DI-001**: System MUST execute all balance-modifying operations (transfers,
  account creation with opening balance) within a single ACID transaction.
- **DI-002**: System MUST use precise decimal arithmetic for all balance
  calculations — floating-point types MUST NOT be used for monetary values.
- **DI-003**: System MUST validate that account balances never fall below zero
  as a result of a transfer (no overdraft unless explicitly configured).
- **DI-004**: System MUST ensure the combined total balance across all accounts is
  conserved by every transfer operation (money is neither created nor destroyed).
- **DI-005**: System MUST validate currency codes against a known set of supported
  currencies at account creation time.
- **DI-006**: Transfers between accounts in different currencies are supported using
  static exchange rates configured at the service level. The transfer amount is
  converted from the source currency to the destination currency at the configured
  rate at the time of the transfer. The exchange rate and converted amount MUST be
  recorded in the transfer audit record.

### Performance Requirements

- **PERF-001**: Balance retrieval MUST complete in under 500 ms at the 95th percentile
  under normal load.
- **PERF-002**: Account creation and fund transfer operations MUST complete in under
  2 seconds at the 95th percentile under normal load.
- **PERF-003**: System MUST handle at least 500 concurrent transfer requests without
  data corruption or deadlocks.

### Key Entities

- **Account**: Represents a financial account. Attributes: unique account number
  (system-generated), owner (unique identifier of the account holder), currency
  (ISO 4217 code, e.g. EUR, USD), balance (non-negative decimal amount).
- **Transfer**: Represents a completed or rejected fund movement. Attributes:
  transfer ID, source account number, destination account number, source amount,
  source currency, destination amount, destination currency, applied exchange rate
  (1.0 for same-currency transfers), timestamp, status (completed / rejected),
  rejection reason (if applicable), idempotency key.
- **Audit Log Entry**: Immutable record of every state-changing operation. Attributes:
  entry ID, operation type, actor identity, affected account(s), amount (if applicable),
  timestamp, outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can create a new account and receive a unique account
  number in a single request.
- **SC-002**: A caller can retrieve the exact current balance of any account they
  are authorized to view, at any time, without stale data.
- **SC-003**: A successful fund transfer is reflected in both account balances
  immediately after the operation completes — no eventual consistency delay for
  same-service balance reads.
- **SC-004**: No transfer operation results in money being created or destroyed;
  the sum of all account balances is conserved across every transfer.
- **SC-005**: Duplicate transfer requests carrying the same idempotency key are
  safely de-duplicated — exactly one debit/credit pair occurs.
- **SC-006**: All write operations (create, transfer, delete) produce a corresponding
  audit log entry queryable by authorized personnel.
- **SC-007**: The service correctly rejects 100% of transfers where source funds are
  insufficient, with no partial state changes.
- **SC-008**: Balance retrieval responds within 500 ms for 95% of requests under
  expected load; transfer operations complete within 2 seconds for 95% of requests.
- **SC-009**: Transfer requests exceeding the configured per-currency maximum amount
  are rejected 100% of the time with no partial state change.
- **SC-010**: Multi-currency transfers apply the configured static exchange rate,
  and the rate plus converted amount are recorded in every transfer's audit entry.

## Assumptions

- Account numbers are system-generated (not supplied by the caller) and guaranteed
  unique within the service.
- Owner identifiers are opaque strings managed by an external identity system; the
  Fund Transfer Service trusts but does not validate them beyond non-empty presence.
- All monetary amounts are expressed in the account's designated currency; multi-currency
  transfers are supported via static exchange rates configured at the service level.
  Exchange rates are not fetched at runtime and do not change during a transfer.
- A maximum transfer amount is enforced per currency via service configuration
  (e.g. 1,000,000 EUR per single transfer). The limit is not per-account or cumulative.
- Overdraft (negative balance) is not permitted; all transfers must be fully covered
  by the source account's current balance.
- "Delete account" is a hard delete (or logical close); historical transfer records
  and audit logs referencing the account are retained for compliance purposes.
- A single supported-currency list is maintained as service configuration and is not
  dynamically updated at runtime.
- Authentication is provided by an upstream identity/API-gateway layer; the service
  enforces authorization but delegates authentication token issuance externally.
- Transfer idempotency is client-driven via a caller-supplied idempotency key; the
  service stores and checks this key to detect duplicates.
