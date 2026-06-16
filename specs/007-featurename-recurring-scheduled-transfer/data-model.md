# Data Model: Recurring Scheduled Transfer

**Phase**: 1 — Design | **Date**: 2026-06-16
**References**: [spec.md](./spec.md) | [research.md](./research.md) | [plan.md](./plan.md)

---

## Entities

### TransferSchedule

The authoritative record of a user's recurring transfer configuration.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, not null | System-generated identifier |
| `user_id` | UUID | not null, FK → users | Owning user (enforces isolation) |
| `name` | VARCHAR(200) | not null | User-defined label (e.g., "Monthly Rent") |
| `source_account_id` | UUID | not null | Source account for funds |
| `beneficiary_id` | UUID | not null | Pre-registered beneficiary |
| `amount` | NUMERIC(20,8) | not null, > 0 | Transfer amount (never float) |
| `currency` | CHAR(3) | not null | ISO 4217 currency code |
| `interval` | VARCHAR(20) | not null | `daily`, `weekly`, `fortnightly`, `monthly`, `quarterly`, `annually` |
| `start_date` | DATE | not null | First scheduled occurrence |
| `end_date` | DATE | not null | Last possible occurrence date |
| `jurisdiction` | CHAR(2) | not null, default `AT` | ISO 3166-1 alpha-2 for holiday calendar |
| `business_day_rule` | VARCHAR(10) | not null, default `next` | `next`, `previous`, `skip` |
| `status` | VARCHAR(20) | not null, default `ACTIVE` | See State Machine below |
| `version` | INTEGER | not null, default 1 | Increments on every write |
| `next_execution_date` | DATE | nullable | Pre-calculated next due date |
| `last_executed_at` | TIMESTAMPTZ | nullable | Timestamp of last successful execution |
| `execution_count` | INTEGER | not null, default 0 | Count of successful executions |
| `delegated_jwt` | TEXT | not null | Encrypted delegated identity JWT (AES-256) |
| `delegated_jwt_expires_at` | TIMESTAMPTZ | not null | Expiry of the delegated JWT |
| `notify_on_success` | BOOLEAN | not null, default true | Send success notification |
| `notify_on_failure` | BOOLEAN | not null, default true | Send failure notification |
| `notify_advance_hours` | INTEGER | not null, default 24 | Hours before execution for reminder |
| `email_notifications` | BOOLEAN | not null, default true | Opt-in for email channel |
| `created_at` | TIMESTAMPTZ | not null, server-set | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | not null, server-set | Last modification timestamp |

**Indexes**:
- `PK` on `id`
- `idx_schedule_user_status` on `(user_id, status)` — schedule list queries
- `idx_schedule_next_execution` on `(next_execution_date, status)` WHERE `status = 'ACTIVE'` — scheduler polling
- `idx_schedule_user_count` on `(user_id)` WHERE `status IN ('ACTIVE','PAUSED')` — limit enforcement

**Validation rules**:
- `start_date` MUST be ≥ tomorrow (server date)
- `end_date` MUST be > `start_date`
- At least one occurrence MUST fall within `[start_date, end_date]` given `interval`
- `amount` MUST NOT exceed the user's applicable single-transfer limit
- Per-user limit: max 200 schedules with `status IN ('ACTIVE','PAUSED')`

---

### ScheduleExecution

Immutable record of a single execution attempt for a `TransferSchedule`. Append-only.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, not null | System-generated identifier |
| `schedule_id` | UUID | not null, FK → transfer_schedules | Parent schedule |
| `schedule_version` | INTEGER | not null | Version of schedule at time of execution |
| `idempotency_key` | VARCHAR(255) | not null, UNIQUE | `{schedule_id}#{occurrence_date}#{schedule_version}` |
| `occurrence_date` | DATE | not null | Original date from recurrence rule |
| `execution_date` | DATE | not null | Adjusted date (after business-day rule applied) |
| `status` | VARCHAR(20) | not null | `PENDING`, `SUCCEEDED`, `FAILED`, `SKIPPED` |
| `amount` | NUMERIC(20,8) | not null | Amount at time of execution |
| `currency` | CHAR(3) | not null | Currency at time of execution |
| `transfer_id` | UUID | nullable | ID of resulting transfer (when `SUCCEEDED`) |
| `failure_reason` | TEXT | nullable | Human-readable reason (when `FAILED`) |
| `failure_category` | VARCHAR(20) | nullable | `TRANSIENT` or `PERMANENT` |
| `attempt_count` | INTEGER | not null, default 1 | Retry attempt number |
| `initiated_at` | TIMESTAMPTZ | not null, server-set | When this execution attempt began |
| `completed_at` | TIMESTAMPTZ | nullable | When this execution attempt concluded |

**Indexes**:
- `PK` on `id`
- `UNIQUE` on `idempotency_key` — idempotency enforcement (Layer 2)
- `UNIQUE` on `(schedule_id, occurrence_date)` WHERE `status = 'SUCCEEDED'` — prevents double execution
- `idx_execution_schedule` on `(schedule_id, occurrence_date DESC)` — execution history queries

**Immutability**: No UPDATE or DELETE permitted on this table in application code. DB-level trigger enforces append-only. Records are the audit-grade execution history.

---

### AuditLog (extended from spec 001)

Extended with `SCHEDULE_*` operation types. No schema change — existing table absorbs new `operation_type` values.

| `operation_type` value | Triggered by |
|------------------------|-------------|
| `SCHEDULE_CREATED` | User creates a new schedule |
| `SCHEDULE_MODIFIED` | User updates amount, end date, or notification prefs |
| `SCHEDULE_PAUSED` | User pauses schedule |
| `SCHEDULE_RESUMED` | User resumes a paused schedule |
| `SCHEDULE_CANCELLED` | User cancels a schedule |
| `SCHEDULE_COMPLETED` | System marks schedule complete after final execution |
| `SCHEDULE_EXECUTION_SUCCEEDED` | Scheduler executes transfer successfully |
| `SCHEDULE_EXECUTION_FAILED` | Execution attempt fails |
| `SCHEDULE_EXECUTION_SKIPPED` | Occurrence skipped (business_day_rule = skip, or missed window) |

For scheduler-initiated entries, `initiator` = `"system/scheduler (on behalf of user/{user_sub})"`.

---

## State Machine: TransferSchedule.status

```
                    ┌─────────────────────────────┐
                    │                             │
          pause     ▼          resume             │
ACTIVE ─────────► PAUSED ─────────────────────► ACTIVE
  │                                               │
  │ cancel                             cancel     │
  ▼                                               ▼
CANCELLED ◄──────────────────────────────── CANCELLED
  
ACTIVE ──── execution fails (permanent) ───► EXECUTION_FAILED
                                                  │
EXECUTION_FAILED ── user resolves + resumes ──► ACTIVE

ACTIVE ──── final execution completes ──────► COMPLETED
```

**Permitted transitions**:

| From | To | Actor | Condition |
|------|----|-------|-----------|
| `ACTIVE` | `PAUSED` | User | Any time |
| `PAUSED` | `ACTIVE` | User | Any time |
| `ACTIVE` | `CANCELLED` | User | Any time |
| `PAUSED` | `CANCELLED` | User | Any time |
| `ACTIVE` | `EXECUTION_FAILED` | Scheduler | Permanent failure on execution |
| `EXECUTION_FAILED` | `ACTIVE` | User | After resolving underlying issue |
| `ACTIVE` | `COMPLETED` | Scheduler | Final occurrence executed successfully |

**Terminal states** (no further transitions): `CANCELLED`, `COMPLETED`

---

## Relationships

```
users (1) ──────────────────── (N) transfer_schedules
transfer_schedules (1) ──────── (N) schedule_executions
transfer_schedules (N) ──────── (1) beneficiaries      [existing entity]
transfer_schedules (N) ──────── (1) accounts           [existing entity, source]
schedule_executions (N) ──────── (1) transfers          [existing entity, spec 001]
transfer_schedules (1) ──────── (N) audit_log           [existing entity]
schedule_executions (1) ──────── (1) audit_log          [one entry per execution]
```

---

## APScheduler Job Table

APScheduler auto-manages a `scheduled_jobs` table (or configurable name). Schema is internal to APScheduler and should not be written to directly by application code. It stores serialised job state and next fire time. Treated as infrastructure, not application data — excluded from application migrations.
