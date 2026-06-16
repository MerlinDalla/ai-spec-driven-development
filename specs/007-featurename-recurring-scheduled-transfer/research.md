# Research: Recurring Scheduled Transfer

**Phase**: 0 — Research | **Date**: 2026-06-16
**References**: [spec.md](./spec.md) | [plan.md](./plan.md)

All NEEDS CLARIFICATION items resolved. Decisions documented below.

---

## Decision 1: Scheduling Engine

**Decision**: APScheduler 3.10 with `SQLAlchemyJobStore` backed by the existing PostgreSQL 16 instance.

**Rationale**: The project already runs on Python 3.12 / FastAPI / PostgreSQL 16 with SQLAlchemy 2.0. APScheduler integrates natively — no additional broker (Redis, RabbitMQ) or worker process is needed. The scheduler starts inside the FastAPI `lifespan` context as an `AsyncIOScheduler`, uses the existing DB connection pool, and stores job state in a `scheduled_jobs` table managed automatically by APScheduler. PostgreSQL advisory locks (`pg_try_advisory_lock`) provide distributed-safe execution when multiple service instances are running.

**Alternatives considered**:
- **Celery Beat**: Requires a separate message broker (Redis or RabbitMQ) and a dedicated Celery worker process — significant operational overhead for an existing single-service deployment. Rejected: violates KISS for this stack.
- **pg_cron**: Runs inside PostgreSQL, has no access to application context (user identity, audit logging, HTTP clients). Cannot carry delegated identity. Rejected: unsuitable for application-level business logic.

---

## Decision 2: Idempotent Execution (Three-Layer Defence)

**Decision**: Combine an application-level idempotency key, a PostgreSQL unique constraint, and a PostgreSQL advisory lock.

**Layer 1 — Idempotency key**: Each `ScheduleExecution` record carries a composite key: `{schedule_id}#{occurrence_date}#{schedule_version}`. The version component ensures that if the user modifies the schedule, a new idempotency key is generated for future occurrences — preventing stale deduplications.

**Layer 2 — Unique constraint**: A `UNIQUE` index on `(schedule_id, occurrence_date)` with a `WHERE status = 'EXECUTED'` partial filter on the `schedule_executions` table. A second attempt to insert a completed execution raises `IntegrityError`, which is caught and treated as a no-op.

**Layer 3 — Advisory lock**: Before executing, the job handler calls `SELECT pg_try_advisory_lock(hashtext(idempotency_key))`. If it cannot acquire the lock, another instance is already executing this occurrence — the handler exits immediately and APScheduler reschedules a short retry. The lock is released (via `pg_advisory_unlock`) when the handler exits.

**Rationale**: Banking-grade crash safety. Idempotency key survives DB restarts. Unique constraint prevents double-write. Advisory lock prevents race conditions between concurrent scheduler instances. The combination is robust without requiring a distributed coordinator.

**Alternatives considered**:
- Application-only idempotency (no DB constraint): Vulnerable to race conditions under concurrent scale-out. Rejected.
- Celery task uniqueness: Broker-based deduplication is weaker and introduces the broker dependency. Rejected.

---

## Decision 3: Delegated User Identity

**Decision**: Encrypted, scope-narrowed JWT generated at schedule creation time, stored encrypted in the `transfer_schedules` table, decrypted and validated at each execution.

**Mechanism**:
1. At schedule creation (live user session present): generate a JWT with `sub` = user ID, `act` = `scheduler`, `scope` = `{source_account_id, beneficiary_id, max_amount}`, `exp` = 30 days.
2. Encrypt the JWT with a key held in the platform secret store (not in source or Git config). Store the encrypted token in `transfer_schedules.delegated_jwt`.
3. At execution time (no live session): decrypt, verify signature and expiry, extract `sub` and scope. Enforce scope constraints before calling the fund transfer service.
4. Audit log `initiator` is set to `system/scheduler (on behalf of user/{user_sub})` — this is the compliance-critical identity string.
5. Delegated JWT expires after 30 days. The schedule is automatically suspended and the user is notified to re-authenticate and renew.

**Rationale**: Full audit traceability (user identity is always known), least-privilege execution (scheduler can only do what the scoped JWT permits), time-limited blast radius, no ambient system trust.

**Alternatives considered**:
- Service account with user ID stored separately: No cryptographic binding between the service account and the user's authorisation at schedule creation. Easier to forge or misuse. Rejected.
- OAuth2 refresh token stored per schedule: Couples the scheduler to the upstream IdP token endpoint at execution time; network failure → execution failure. Rejected.

---

## Decision 4: Business-Day Calculation

**Decision**: `workalendar` library (80+ jurisdictions, built-in TARGET2 and banking calendars), configured per schedule's `jurisdiction` field (ISO 3166-1 alpha-2, default `AT` for Austria).

**Mechanism**: At schedule creation, calculate all future execution dates from the recurrence rule. For each calculated date, call `workalendar.is_working_day(date, jurisdiction)`. If the date is not a working day, advance to the next working day (configurable per schedule: `next`, `previous`, or `skip`). Store both `scheduled_date` (original) and `execution_date` (adjusted) in `schedule_executions`.

**Rationale**: `workalendar` includes TARGET2 (the Eurozone interbank settlement calendar), Austrian, German, and 80+ other jurisdictions out of the box. Field-tested in banking systems. Extensible via subclassing for custom bank-specific closures. Per-jurisdiction configuration enables multi-currency, multi-region expansion without code changes.

**Alternatives considered**:
- `python-holidays`: Lighter, but no TARGET2 calendar built-in; custom banking calendar setup required. Rejected in favour of `workalendar`'s built-in banking calendars. *(Plan.md Technical Context references `python-holidays` — this corrects that: `workalendar` is the chosen library.)*
- `pandas.bdate_range`: Time-series tool, not a banking calendar library; requires building custom calendar classes. Rejected.

---

## Decision 5: Architecture Evidence Artefacts

**Decision**: Produce two security artefacts in `docs/security/` as part of Phase 1:

1. **S-ADR**: `docs/security/adr/s-adr-001-scheduler-delegated-identity.md` — documents the delegated identity architectural decision (Decision 3 above) as a formal Security Architecture Decision Record.
2. **STRIDE Threat Model**: `docs/security/threat-model-recurring-transfer.md` — documents all identified threats against the three trust boundaries, with CIA impact and mitigations.

**Rationale**: Constitution Principle VIII (Secure Architecture Governance) mandates S-ADRs for architecturally significant decisions and STRIDE threat models for new trust boundaries. The scheduler-to-payment-engine boundary and the delegated identity mechanism both qualify.
