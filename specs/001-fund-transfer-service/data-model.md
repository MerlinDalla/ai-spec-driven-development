# Data Model: Fund Transfer Service

**Phase**: 1 — Design | **Date**: 2026-06-15
**References**: [spec.md](./spec.md) | [research.md](./research.md)

---

## Overview

The service manages three primary entities and one supporting table:

| Entity | Table | Purpose |
|--------|-------|---------|
| Account | `accounts` | Financial account: number, owner, currency, balance |
| Transfer | `transfers` | Fund movement record with idempotency + audit data |
| AuditLogEntry | `audit_log` | Immutable write-operation history (compliance) |
| IdempotencyKey | `idempotency_keys` | Duplicate-transfer guard (24 h TTL) |

---

## Entity: Account

**Description**: Represents a financial account owned by one party, denominated in a
single currency. Balances use exact decimal arithmetic (`NUMERIC(19, 4)`).

### Fields

| Field | Column | DB Type | Python Type | Rules |
|-------|--------|---------|-------------|-------|
| `id` | `id` | `UUID` PK | `uuid.UUID` | System-generated (UUIDv4) |
| `account_number` | `account_number` | `VARCHAR(34)` UNIQUE NOT NULL | `str` | System-generated, globally unique; format: `ACCT-<12 alphanum>` |
| `owner_id` | `owner_id` | `TEXT` NOT NULL | `str` | Opaque string from upstream IdP JWT `sub` claim; non-empty |
| `currency` | `currency` | `CHAR(3)` NOT NULL | `str` | ISO 4217 code; must be in configured supported currencies list |
| `balance` | `balance` | `NUMERIC(19, 4)` NOT NULL | `Decimal` | ≥ 0; set to opening balance at creation; never negative |
| `status` | `status` | `VARCHAR(20)` NOT NULL | `AccountStatus` | `active` | `closed`; default `active` |
| `owner_pii_hash` | `owner_pii_hash` | `VARCHAR(64)` | `str` | SHA-256 of owner_id — allows PII anonymization on deletion |
| `created_at` | `created_at` | `TIMESTAMPTZ` NOT NULL | `datetime` | DB server default `now()` |
| `updated_at` | `updated_at` | `TIMESTAMPTZ` NOT NULL | `datetime` | Updated on every balance change |

### Indexes

```sql
CREATE UNIQUE INDEX accounts_account_number_idx ON accounts (account_number);
CREATE INDEX accounts_owner_id_idx ON accounts (owner_id);
CREATE INDEX accounts_status_idx ON accounts (status);
```

### Validation Rules

- `opening_balance` (at creation): `>= 0` (Decimal); required
- `currency`: must be in `supported_currencies` from config
- `owner_id`: non-empty string; max 255 chars
- `account_number`: auto-generated; never supplied by caller
- `status=closed` accounts: reject all balance reads, transfers, and deletes with 404

### State Transitions

```
active ──[DELETE with balance=0]──► closed
active ──[transfer credit/debit]──► active (balance updated)
```

- `closed` is terminal — no transitions out
- Deletion physically sets `status='closed'` and anonymizes `owner_id` (GDPR)
- Historical transfers referencing a closed account retain account number (audit compliance)

---

## Entity: Transfer

**Description**: An immutable record of a fund movement attempt. Created on every
`POST /api/v1/transfers` call that passes idempotency check. Both completed and
rejected transfers are persisted.

### Fields

| Field | Column | DB Type | Python Type | Rules |
|-------|--------|---------|-------------|-------|
| `id` | `id` | `UUID` PK | `uuid.UUID` | System-generated (UUIDv4) |
| `idempotency_key` | `idempotency_key` | `VARCHAR(255)` UNIQUE NOT NULL | `str` | Caller-supplied `X-Idempotency-Key`; max 255 chars |
| `source_account_number` | `source_account_number` | `VARCHAR(34)` NOT NULL | `str` | FK → accounts.account_number (retained even if account closed) |
| `destination_account_number` | `destination_account_number` | `VARCHAR(34)` NOT NULL | `str` | FK → accounts.account_number |
| `source_amount` | `source_amount` | `NUMERIC(19, 4)` NOT NULL | `Decimal` | > 0; amount in source currency as requested |
| `source_currency` | `source_currency` | `CHAR(3)` NOT NULL | `str` | ISO 4217; matches source account currency |
| `destination_amount` | `destination_amount` | `NUMERIC(19, 4)` NOT NULL | `Decimal` | > 0; source_amount × exchange_rate |
| `destination_currency` | `destination_currency` | `CHAR(3)` NOT NULL | `str` | ISO 4217; matches destination account currency |
| `exchange_rate` | `exchange_rate` | `NUMERIC(20, 8)` NOT NULL | `Decimal` | Applied rate at transfer time; `1.00000000` for same-currency |
| `status` | `status` | `VARCHAR(20)` NOT NULL | `TransferStatus` | `completed` | `rejected` |
| `rejection_reason` | `rejection_reason` | `TEXT` | `str | None` | Populated on status=rejected; null on completed |
| `caller_id` | `caller_id` | `TEXT` NOT NULL | `str` | JWT `sub` of the caller who initiated this transfer |
| `created_at` | `created_at` | `TIMESTAMPTZ` NOT NULL | `datetime` | Immutable; DB server default `now()` |

### Indexes

```sql
CREATE UNIQUE INDEX transfers_idempotency_key_idx ON transfers (idempotency_key);
CREATE INDEX transfers_source_account_idx ON transfers (source_account_number);
CREATE INDEX transfers_destination_account_idx ON transfers (destination_account_number);
CREATE INDEX transfers_created_at_idx ON transfers (created_at DESC);
```

### Validation Rules

- `source_account_number != destination_account_number` (self-transfer rejected)
- `source_amount > 0` (Decimal)
- `source_amount <= max_transfer_amounts[source_currency]` from config
- Source account must have `status='active'` and `balance >= source_amount`
- Destination account must have `status='active'`
- Source and destination currencies must both be in supported_currencies

### Invariants (enforced within a single ACID transaction)

1. `source_account.balance -= source_amount` (after transfer)
2. `destination_account.balance += destination_amount` (after transfer)
3. Total balance conserved: `Σ(all balances)` is unchanged for same-currency transfers
4. Idempotency: same `X-Idempotency-Key` always produces the same outcome

---

## Entity: AuditLogEntry

**Description**: Immutable record of every state-changing operation. Written in the
same transaction as the operation it records. Never updated or deleted.

### Fields

| Field | Column | DB Type | Python Type | Rules |
|-------|--------|---------|-------------|-------|
| `id` | `id` | `UUID` PK | `uuid.UUID` | System-generated (UUIDv4) |
| `operation_type` | `operation_type` | `VARCHAR(30)` NOT NULL | `OperationType` | `account_created` | `account_deleted` | `transfer_completed` | `transfer_rejected` |
| `actor_identity` | `actor_identity` | `TEXT` NOT NULL | `str` | JWT `sub` of the caller; `system` for automated ops |
| `affected_account_numbers` | `affected_account_numbers` | `TEXT[]` NOT NULL | `list[str]` | Accounts involved (1 for account ops, 2 for transfers) |
| `amount` | `amount` | `NUMERIC(19, 4)` | `Decimal | None` | Transfer amount (source); null for non-transfer ops |
| `currency` | `currency` | `CHAR(3)` | `str | None` | Source currency for transfers; account currency for account ops |
| `outcome` | `outcome` | `VARCHAR(20)` NOT NULL | `str` | `success` | `failure` |
| `detail` | `detail` | `JSONB` | `dict | None` | Structured extra context (rejection reason, rate applied, etc.) |
| `timestamp` | `timestamp` | `TIMESTAMPTZ` NOT NULL | `datetime` | DB server default `now()`; immutable |
| `request_id` | `request_id` | `TEXT` | `str | None` | `X-Request-ID` from the inbound request (correlation) |

### Indexes

```sql
CREATE INDEX audit_log_actor_identity_idx ON audit_log (actor_identity);
CREATE INDEX audit_log_affected_accounts_idx ON audit_log USING GIN (affected_account_numbers);
CREATE INDEX audit_log_timestamp_idx ON audit_log (timestamp DESC);
CREATE INDEX audit_log_operation_type_idx ON audit_log (operation_type);
```

### Rules

- Rows are INSERT-only: no UPDATE, no DELETE
- Written in same DB transaction as the operation
- Retained indefinitely (compliance retention period applies)
- On account deletion, audit log entries are NOT modified (account number retained for traceability)

---

## Supporting Table: IdempotencyKey

**Description**: Stores the outcome of each processed transfer request to enable
safe replay of duplicate requests. Entries expire after 24 hours.

### Fields

| Field | Column | DB Type | Rules |
|-------|--------|---------|-------|
| `key` | `key` | `VARCHAR(255)` PK | Caller-supplied X-Idempotency-Key |
| `owner_id` | `owner_id` | `TEXT` NOT NULL | Must match JWT sub; prevents cross-caller reuse |
| `request_hash` | `request_hash` | `VARCHAR(64)` NOT NULL | SHA-256 of request body; mismatch → 409 |
| `response_body` | `response_body` | `JSONB` | Stored response to replay |
| `response_status` | `response_status` | `SMALLINT` | HTTP status to replay |
| `status` | `status` | `VARCHAR(20)` NOT NULL | `in_progress` | `complete` | `failed` |
| `created_at` | `created_at` | `TIMESTAMPTZ` NOT NULL | Immutable |
| `expires_at` | `expires_at` | `TIMESTAMPTZ` NOT NULL | `created_at + 24 hours`; expired → re-process |

### Indexes

```sql
CREATE INDEX idempotency_keys_expires_at_idx ON idempotency_keys (expires_at);
```

---

## Relationships

```
accounts  1 ──── * transfers (via source_account_number)
accounts  1 ──── * transfers (via destination_account_number)
transfers 1 ──── 1 idempotency_keys (via idempotency_key)
[any write op] 1 ──── 1..* audit_log (written in same transaction)
```

---

## Currency and Limit Configuration (not a DB table)

Managed as a YAML config file (`config/exchange_rates.yaml`) loaded at startup:
- `supported_currencies`: list of valid ISO 4217 codes
- `max_transfer_amounts`: per-currency maximum single transfer amount
- `rates`: nested dict — `rates[from_currency][to_currency]` → Decimal string

See [research.md](./research.md#6-exchange-rate-configuration) for full YAML structure.

---

## Constitution Re-Check (Post-Design)

- [x] ACID: All balance writes + audit log in single transaction ✅
- [x] Decimal: `NUMERIC(19, 4)` for amounts; `NUMERIC(20, 8)` for exchange rates ✅
- [x] Audit trail: `audit_log` table, INSERT-only, written in same transaction ✅
- [x] PII: `owner_id` stored as TEXT; anonymized on account deletion; hash retained ✅
- [x] No floating point: YAML rates stored as strings → Decimal; never float ✅
- [x] Idempotency: `idempotency_keys` table guards duplicate transfers ✅
- [x] Conservation invariant: debit == credit enforced in service layer ✅