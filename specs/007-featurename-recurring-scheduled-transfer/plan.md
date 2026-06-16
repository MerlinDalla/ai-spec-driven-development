# Implementation Plan: Recurring Scheduled Transfer

**Branch**: `007-featurename-recurring-scheduled-transfer` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/007-featurename-recurring-scheduled-transfer/spec.md`

## Summary

Extend the Fund Transfer Service (spec 001) with a recurring-transfer scheduling subsystem.
Users define a schedule (beneficiary, amount, currency, interval, start date, end date);
the system executes the corresponding fund transfer automatically on each due date until
the schedule completes or is cancelled. The subsystem introduces a persistent scheduler
backed by the existing PostgreSQL instance, a delegated-identity execution model (scheduler
acts on behalf of the absent user), idempotent execution with database-level locking,
business-day adjustment via jurisdiction calendars, and a full STRIDE threat model with
an S-ADR covering the new trust boundary between the user-facing API and the autonomous
scheduling engine.

## Technical Context

**Language/Version**: Python 3.12 (matches Fund Transfer Service, spec 001)

**Primary Dependencies** (additions to spec 001 baseline):
- APScheduler 3.10 + `apscheduler[sqlalchemy]` — persistent job scheduler with
  `SQLAlchemyJobStore` on the existing PostgreSQL instance; no separate broker required
- `workalendar` 0.15+ — jurisdiction-specific bank holiday calendar for
  next-business-day calculation (includes TARGET2 and Austrian/German calendars)
- `python-jose` + `cryptography` — already present; reused for delegated identity token
  generation (system-scoped short-lived JWT carrying user `sub`)
- All other dependencies inherited from spec 001 (FastAPI, SQLAlchemy 2.0 async,
  Pydantic v2, Alembic, structlog, prometheus, OpenTelemetry, pytest)

**Storage**: PostgreSQL 16 — existing instance extended with:
- `transfer_schedules` table (schedule definitions, state machine)
- `schedule_executions` table (immutable execution history)
- `apscheduler_jobs` table (APScheduler job store — auto-managed by APScheduler)
- `audit_log` entries for all schedule lifecycle events (appended to existing table)

**Testing**: pytest + pytest-asyncio + httpx; APScheduler jobs tested with
`MemoryJobStore` in unit tests; integration tests use real PostgreSQL via docker-compose

**Target Platform**: Linux container (Docker); same docker-compose as spec 001

**Project Type**: REST web service extension (backend only); scheduler runs as an
in-process background service within the same FastAPI application process

**Performance Goals**:
- Schedule CRUD endpoints: < 500 ms p95 (reads), < 2 s p95 (writes)
- Scheduled transfer execution latency: within 5 minutes of scheduled time
- Support 10,000 active schedules across all users without execution lag

**Constraints**:
- No floating-point for monetary amounts — `decimal.Decimal` / `NUMERIC(20,8)`
- Scheduler identity: short-lived system JWT carrying user `sub`; never uses
  user's original session token
- Idempotency: per-occurrence idempotency key (`schedule_id + occurrence_date`)
  stored in `schedule_executions`; duplicate execution attempts are detected and
  no-op'd via `SELECT FOR UPDATE SKIP LOCKED`
- Business-day adjustment: configurable per schedule's currency/jurisdiction;
  defaults to AT (Austria) holiday calendar
- FX recurring transfers: out of scope for this plan (spec 002 extension deferred)

**Scale/Scope**: Up to 10,000 active schedules; up to 200 schedules per user;
execution throughput up to ~500 transfers/minute at peak (monthly billing day)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Security-First & Compliance**:
- [x] Authentication/authorization strategy defined — all CRUD endpoints require JWT;
      scheduler uses delegated system JWT carrying user `sub`
- [x] Sensitive data encryption approach specified — beneficiary account numbers masked
      in API responses and notifications; stored encrypted at rest via PostgreSQL TDE
- [x] Audit logging requirements identified — full `SCHEDULE_*` vocabulary defined in spec
- [x] Security scanning integration confirmed — inherited from spec 001 CI pipeline
- [x] Secrets management approach documented — scheduler signing key in platform secret
      store (not in code/config); rotatable independently of application secrets

**Data Integrity & Auditability**:
- [x] ACID transaction boundaries identified — schedule write + audit entry in single
      transaction; execution + transfer call + execution record + audit entry in single transaction
- [x] Decimal type usage confirmed — `NUMERIC(20,8)` for all monetary columns; Python `decimal.Decimal`
- [x] Audit trail requirements specified — 9-value `operation_type` enum defined in spec DI-005
- [x] Data validation strategy defined — Pydantic v2 at API boundary; DB constraints as second layer
- [x] `audit_log` table defined with mandatory columns — inherits from spec 001; `initiator`
      set to `system/scheduler:<user_sub>` for autonomous executions
- [x] `operation_type` controlled vocabulary documented — `SCHEDULE_CREATED`,
      `SCHEDULE_MODIFIED`, `SCHEDULE_PAUSED`, `SCHEDULE_RESUMED`, `SCHEDULE_CANCELLED`,
      `SCHEDULE_COMPLETED`, `SCHEDULE_EXECUTION_SUCCEEDED`, `SCHEDULE_EXECUTION_FAILED`,
      `SCHEDULE_EXECUTION_SKIPPED`
- [x] All state-changing operations mapped to an audit entry type — yes, see above
- [x] Audit writes in same ACID transaction as triggering operation — enforced
- [x] Audit table append-only — enforced at DB level (trigger blocks UPDATE/DELETE)

**API-Driven Design**:
- [x] API contract format chosen — OpenAPI 3.1 (consistent with spec 001)
- [x] Versioning strategy defined — `/v1/schedules` prefix; breaking changes → `/v2/`
- [x] Backward compatibility approach specified — one major version maintained simultaneously
- [x] Request/response validation — Pydantic v2 schemas; validated against OpenAPI contract

**Test-First Development**:
- [x] Test framework selected — pytest + pytest-asyncio + httpx
- [x] TDD workflow confirmed — tests written before implementation per constitution
- [x] Coverage targets — unit > 95% (schedule state machine, business-day calc, idempotency);
      integration > 80%
- [x] Contract testing — Schemathesis against generated OpenAPI spec

**Resilience & Error Handling**:
- [x] Timeout and retry strategies defined — transfer execution calls: 30 s timeout,
      3 retries with exponential backoff; transient failures retry; permanent failures
      (e.g., account closed) move schedule to `EXECUTION_FAILED` without retry
- [x] Circuit breaker planned — Tenacity circuit breaker wrapping fund-transfer calls
- [x] Error categorization — transient (network, timeout) vs permanent (insufficient funds,
      closed account, limit exceeded); different state transitions per category
- [x] Idempotency guarantees — per-occurrence idempotency key; `SELECT FOR UPDATE SKIP LOCKED`
      prevents duplicate execution of same occurrence

**Performance & Scalability**:
- [x] Performance targets documented — < 500 ms read, < 2 s write, execution within 5 min
- [x] Database optimization — index on `(user_id, status)` for schedule list queries;
      index on `(next_execution_at, status)` for scheduler polling; partial index on
      `ACTIVE` schedules only
- [x] Load testing — Locust scenarios for schedule CRUD and concurrent execution bursts
- [x] Resource monitoring — Prometheus metrics: `schedules_active_total`, `executions_total`,
      `execution_lag_seconds` histogram

**Observability & Monitoring**:
- [x] Logging strategy — structlog JSON; every execution logs schedule_id, user_sub,
      occurrence_date, outcome, duration
- [x] Metrics — `schedules_active_total` (gauge by status), `execution_lag_seconds`
      (histogram), `executions_total` (counter by outcome)
- [x] Distributed tracing — OpenTelemetry spans for scheduler tick, execution attempt,
      and fund-transfer call; trace ID carried across async boundary
- [x] Alert definitions — alert if `execution_lag_seconds` p95 > 300 s; alert if
      `executions_total{outcome="failed"}` rate > 5% over 5 min window

**Secure Architecture Governance**:
- [x] Trust boundaries identified — (1) User↔API (JWT auth); (2) API↔Scheduler Engine
      (in-process, but scheduler acts with delegated identity); (3) Scheduler↔Fund Transfer
      execution (internal service call with scoped system JWT)
- [x] STRIDE threat model initiated — see `docs/security/threat-model-recurring-transfer.md`
      (generated in Phase 1)
- [x] S-ADR created — `docs/security/adr/s-adr-001-scheduler-delegated-identity.md`
      (generated in Phase 1)
- [x] Zero Trust applicability evaluated — scheduler carries verified per-user-scoped
      JWT; no ambient system trust; evaluated and documented in S-ADR
- [x] Supply-chain — `python-holidays`, `APScheduler` from PyPI with pinned versions
      and hash verification in `requirements.txt`; lock file committed
- [x] Secrets management — scheduler signing key in platform secret store; injected
      via environment variable at runtime; never in source or Git config
- [x] Evidence directory — `docs/security/` planned; S-ADR and threat model to be
      created in Phase 1

**Compliance**:
- [x] Applicable regulations — PCI-DSS (recurring payment data), GDPR (schedule retention,
      right to be forgotten), AML/KYC (threshold alerts for recurring high-value transfers)
- [x] Data classification — schedule amount + beneficiary = financial PII; masked in
      responses and logs; full value only in encrypted storage
- [x] Privacy impact assessment — required; recurring transfer data reveals spending
      patterns; assessment to be conducted before production launch

## Project Structure

### Documentation (this feature)

```text
specs/007-featurename-recurring-scheduled-transfer/
├── plan.md              # This file
├── research.md          # Phase 0 — technology decisions
├── data-model.md        # Phase 1 — entities and state machine
├── quickstart.md        # Phase 1 — validation guide
├── contracts/
│   └── openapi.yaml     # Phase 1 — REST API contract
└── tasks.md             # Phase 2 — generated by /speckit-tasks
```

### Security Evidence

```text
docs/security/
├── threat-model-recurring-transfer.md   # STRIDE threat model (Phase 1)
└── adr/
    └── s-adr-001-scheduler-delegated-identity.md  # S-ADR (Phase 1)
```

### Source Code (additions to existing Fund Transfer Service)

```text
src/
├── schedules/
│   ├── models.py          # TransferSchedule, ScheduleExecution ORM models
│   ├── schemas.py         # Pydantic v2 request/response schemas
│   ├── router.py          # FastAPI router: /v1/schedules CRUD + actions
│   ├── service.py         # Schedule business logic, state machine
│   ├── scheduler.py       # APScheduler setup, job registration, tick handler
│   ├── executor.py        # Execution logic: idempotency, delegated identity, transfer call
│   ├── calendar.py        # Business-day adjustment (python-holidays)
│   └── notifications.py   # Notification event emission
└── schedules/migrations/
    └── versions/          # Alembic migration for schedule tables

tests/
├── unit/
│   └── schedules/         # State machine, calendar, idempotency unit tests
├── integration/
│   └── schedules/         # End-to-end schedule lifecycle tests
└── contract/
    └── schedules/         # Schemathesis OpenAPI contract tests
```

**Structure Decision**: In-process extension of the existing Fund Transfer Service
(Option 1 — single project). The scheduler runs as an APScheduler `AsyncIOScheduler`
started in the FastAPI `lifespan` context manager. No separate microservice or
message broker is introduced, keeping operational complexity low. All new code
lives under `src/schedules/`.

## Complexity Tracking

> No constitution violations. All gates pass.

