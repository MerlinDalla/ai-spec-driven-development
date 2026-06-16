# Implementation Plan: Currency Conversion & Cross-Currency Transfer

**Branch**: `002-currency-fx-transfer` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-currency-fx-transfer/spec.md`

## Summary

Extend the existing Python/FastAPI Fund Transfer Service with a live currency conversion
table (dynamic FX rates, staleness detection, preview calculator) and enhanced cross-currency
transfer support (split fees, PENDING→PROCESSING→COMPLETED/FAILED state machine, pessimistic
locking, in-app notifications). The feature builds on the existing SQLAlchemy async/PostgreSQL
stack and introduces a pluggable `FxRateProvider` protocol, a DB-backed `fx_rate_snapshot`
table, a `notifications` table, and new API endpoints under `/api/v1/fx/`.

## Technical Context

**Language/Version**: Python 3.12 (existing)

**Primary Dependencies** (existing + new):
- FastAPI 0.111 + Uvicorn — ASGI framework (existing)
- SQLAlchemy 2.0 async + asyncpg — ORM/driver (existing)
- Pydantic v2 — request/response validation (existing)
- Alembic — DB migrations (existing)
- structlog — structured logging (existing)
- prometheus-fastapi-instrumentator — metrics (existing)
- opentelemetry-sdk + instrumentation — tracing (existing)
- pytest + pytest-asyncio + httpx — test stack (existing)
- `httpx` async client — FX provider HTTP adapter (new use; already in test dependencies)

**Storage**: PostgreSQL 16 — new tables: `fx_rate_snapshot`, `notifications`;
modified table: `transfers` (new status values, fee columns);
modified enum vocabulary: `OperationType` in `audit_log`.

**Testing**: pytest + pytest-asyncio + httpx (existing stack, no new tools)

**Target Platform**: Linux container (Docker) — unchanged

**Project Type**: REST web service extension (backend only)

**Performance Goals**:
- FX rate table retrieval < 500 ms p95 (served from DB snapshot)
- Conversion preview < 500 ms p95
- Transfer initiation and confirmation < 2 s p95
- >= 500 concurrent transfer sessions without deadlock or data corruption

**Constraints**:
- All monetary amounts in NUMERIC(19,4) / decimal.Decimal
- Exchange rates stored in NUMERIC(20,8) — minimum 6 decimal places
- FX rates served from DB snapshot; provider call only on scheduled or on-demand refresh
- Stale rates block transfer initiation (configurable max age, default 60 min)
- Pessimistic account locking: SELECT FOR UPDATE with DB statement_timeout guard
- In-app notifications only; no email/SMS
- Idempotency key remains caller-supplied (unchanged pattern)

**Scale/Scope**: Same single-service backend; ~500 concurrent users; extends existing feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Security-First & Compliance**:
- [x] Authentication/authorization defined — JWT Bearer (unchanged); all new endpoints require auth; only account owner may initiate transfer
- [x] Sensitive data encryption specified — TLS in transit (unchanged); no new PII fields
- [x] Audit logging identified — new OperationType values: fx_rate_refreshed, cross_currency_transfer_initiated, cross_currency_transfer_completed, cross_currency_transfer_failed, notification_delivered
- [x] Security scanning confirmed — bandit + safety in existing CI pipeline (unchanged)
- [x] Secrets management documented — FX provider credentials via env vars / vault

**Data Integrity & Auditability**:
- [x] ACID transaction boundaries — rate snapshot write, transfer state transitions, audit entries all in single DB transactions
- [x] Decimal type confirmed — NUMERIC(19,4) for fees/amounts; NUMERIC(20,8) for rates
- [x] Audit trail specified — AuditLogEntry extended; fee breakdown in detail JSONB
- [x] Validation strategy — Pydantic v2 at API boundary; stale-rate, balance, fee checks in service layer
- [x] audit_log table defined — existing table satisfies operation_type, id (operation_id), actor_identity (initiator), timestamp (server-set)
- [x] operation_type controlled vocabulary — new values documented in research.md before implementation
- [x] All state-changing ops mapped to audit entry — transfer state changes x3, rate refresh, notification delivery
- [x] Audit writes in same ACID transaction — enforced in service layer; operation rolls back if audit fails
- [x] Audit table append-only — no UPDATE/DELETE on audit_log (existing policy)

**API-Driven Design**:
- [x] API contract chosen — OpenAPI 3.1 (FastAPI auto-generated); contract at specs/002-currency-fx-transfer/contracts/openapi.yaml
- [x] Versioning — URL prefix /api/v1/fx/ for new endpoints; existing /api/v1/transfers/ extended additively
- [x] Backward compatibility — existing endpoints unchanged; new fields additive
- [x] Request/response validation — Pydantic v2 on all new endpoints

**Test-First Development**:
- [x] Test framework — pytest + pytest-asyncio + httpx (unchanged)
- [x] TDD confirmed — tests written first
- [x] Coverage targets — unit >95% for FX math and fee calculations; integration >80%
- [x] Contract testing — httpx tests validate behavior against OpenAPI spec

**Resilience & Error Handling**:
- [x] Timeout/retry for FX provider — 5 s connect, 15 s read, 2 retries exponential backoff; 3 consecutive failures mark snapshot stale
- [x] Circuit breaker — FX provider failures set is_stale=True; transfer initiation blocked
- [x] Error categorization — new: StaleRateError (503), RateDeviationError (409), UnsupportedCurrencyPairError (422)
- [x] Idempotency — unchanged; X-Idempotency-Key required for transfer mutations

**Performance & Scalability**:
- [x] Performance targets — <500 ms p95 read (PERF-001), <2 s p95 write (PERF-002), <10 s p95 refresh (PERF-004); per-request 5 s provider timeout with 2-retry backoff (PERF-005)
- [x] PERF-004 measurement bounds — start: refresh triggered; end: rates committed to DB snapshot and available for reads; error rate ≤1%
- [x] PERF-005 fallback SLA — cached-rate serve MUST complete within PERF-001 budget (≤500ms p95); retry: 2× with 500ms/2× exponential backoff before fallback; timeout configurable via FX_PROVIDER_TIMEOUT_SECONDS
- [x] Concurrent refresh deduplication — concurrent scheduled + on-demand refresh deduplicated to single in-flight provider call (PERF-004)
- [x] Load test gate — 2-min ramp + 10-min sustained at 500 sessions; production-equivalent staging: same CPU/mem tier, ≥10k DB records, network latency within 10% of prod; CI/CD automated enforcement; manual override requires TL sign-off (PERF-006)
- [x] DB optimization — index on fx_rate_snapshot(effective_at); index on notifications(recipient_account_number, read_at)
- [x] Resource monitoring — add fx_rate_age_seconds gauge, fx_rate_refresh_total counter, transfer_status_total counter

**Observability & Monitoring**:
- [x] Logging — structlog JSON; correlation ID on all FX and transfer log lines
- [x] Metrics — fx_rate_age_seconds gauge, fx_rate_refresh_total counter, transfer_status_total by status
- [x] Tracing — OpenTelemetry spans on FxRateProvider.fetch(), transfer state transitions, notification delivery
- [x] Alerts — fx_rate_age_seconds > max_age threshold; FAILED transfer rate > 1%

**Compliance**:
- [x] Regulations — GDPR (unchanged); AML/KYC screening hook on third-party transfers above threshold
- [x] Data classification — exchange rates: internal non-PII; fees: confidential financial; notifications: non-PII operational
- [x] Privacy impact — no new PII fields; notifications reference account numbers (already confidential)

**Constitution Gate Result**: PASS — no violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```
specs/002-currency-fx-transfer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md
└── contracts/
    └── openapi.yaml     # Phase 1 output
```

### Source Code (extensions to existing layout)

```
src/fund_transfer/
├── api/v1/
│   ├── fx.py                            # NEW: GET /fx/rates, GET /fx/convert
│   ├── notifications.py                 # NEW: GET /notifications, PATCH /notifications/{id}/read
│   ├── transfers.py                     # MODIFIED: fee fields + status in response
│   └── router.py                        # MODIFIED: include fx + notifications routers
├── core/
│   ├── config.py                        # MODIFIED: FX_RATE_MAX_AGE_MINUTES, FX_RATE_DEVIATION_THRESHOLD_PCT, FX_PROVIDER_URL
│   └── exceptions.py                    # MODIFIED: StaleRateError, RateDeviationError
├── models/
│   ├── fx_rate_snapshot.py              # NEW
│   ├── notification.py                  # NEW
│   ├── transfer.py                      # MODIFIED: PENDING/PROCESSING/FAILED, sending_fee, receiving_fee
│   └── audit_log.py                     # MODIFIED: new OperationType values
├── repositories/
│   ├── fx_rate_repository.py            # NEW
│   └── notification_repository.py       # NEW
├── schemas/
│   ├── fx.py                            # NEW: RateTableResponse, ConversionPreviewResponse
│   └── notification.py                  # NEW: NotificationResponse
├── services/
│   ├── fx_rate_service.py               # NEW: dynamic rate service (staleness, refresh, deviation check)
│   ├── fx_rate_provider.py              # NEW: FxRateProvider protocol + HttpFxRateProvider + StaticFxRateProvider
│   ├── notification_service.py          # NEW: create and deliver in-app notifications
│   ├── transfer_service.py              # MODIFIED: state machine, split fees, rate deviation, pessimistic lock
│   └── exchange_rate_service.py         # KEPT UNCHANGED (backward compat for same-currency transfers)

alembic/versions/
└── XXXX_add_fx_cross_currency_transfer.py   # NEW migration

tests/
├── contract/
│   ├── test_fx_rates.py                 # NEW
│   └── test_notifications.py            # NEW
├── integration/
│   └── test_cross_currency_transfers.py # NEW
└── unit/
    ├── test_fx_rate_service.py           # NEW
    ├── test_fx_rate_provider.py          # NEW
    └── test_notification_service.py      # NEW
```

**Structure Decision**: Extend existing single-project layered layout (API → Service → Repository → DB model). `exchange_rate_service.py` is kept unchanged; the new `fx_rate_service.py` handles dynamic rates to avoid breaking existing tests.
