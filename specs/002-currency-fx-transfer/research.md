# Research: Currency Conversion & Cross-Currency Transfer

**Feature**: 002-currency-fx-transfer | **Date**: 2026-06-15

All findings are grounded in direct code inspection of the existing `fund_transfer` service.

---

## Codebase Baseline

| Verified Fact | Source |
|---|---|
| `ExchangeRateService` is a concrete class injected via constructor | `services/exchange_rate_service.py:9`, `services/transfer_service.py:57` |
| `transfers.status` is `String(20)` / VARCHAR — NOT a PostgreSQL native ENUM | `models/transfer.py:40`, `alembic/versions/002_transfers_schema.py:32` |
| `rejection_reason TEXT NULL` already exists on `transfers` | `models/transfer.py:41` |
| `audit_log` entries written inside same `session.begin()` as the triggering operation | `services/transfer_service.py:141–157`, `repositories/transfer_repository.py:62–85` |
| No notification model, no WebSocket layer exists | `src/fund_transfer/models/` (3 files: account, audit_log, transfer) |
| FastAPI lifespan hook used for startup operations | `src/fund_transfer/main.py:18–27` |
| Service instances created at router level (singleton per process) | `src/fund_transfer/api/v1/transfers.py:14` |

---

## Decision 1: Pluggable FX Rate Provider Pattern

**Decision**: Use `typing.Protocol` (structural subtyping) with an async interface, injected
via FastAPI `app.state` and the existing constructor-injection pattern.

**Recommended interface**:

```python
# src/fund_transfer/services/fx_rate_provider.py
from typing import Protocol, runtime_checkable
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass

@dataclass(frozen=True)
class RateSnapshot:
    rates: dict[str, dict[str, Decimal]]  # {"EUR": {"USD": Decimal("1.085")}}
    fetched_at: datetime                   # UTC
    provider: str                          # "static_config" | "treasury_feed"

@runtime_checkable
class FxRateProvider(Protocol):
    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal: ...
    async def get_snapshot(self) -> RateSnapshot: ...
    async def is_stale(self) -> bool: ...
    async def refresh(self) -> None: ...
    def validate_currency(self, code: str) -> None: ...
```

**Two concrete implementations**:

- `StaticFxRateProvider` — wraps existing `ExchangeRateConfig`; `is_stale()` always returns
  `False`; `refresh()` is a no-op. Used in tests and for legacy same-currency transfers.
  Satisfies the Protocol *without any modification* to the existing `ExchangeRateService` class.
- `TreasuryFeedAdapter` — async `httpx.AsyncClient`; fetches from `FX_PROVIDER_URL`;
  5 s connect timeout, 15 s read timeout, 2 retries with exponential backoff;
  uses `asyncio.Lock` to prevent thundering herd on concurrent refresh;
  raises `StaleRateError` if 3 consecutive fetches fail.

**FastAPI wiring** (extends existing lifespan in `main.py`):

```python
# Startup: initial fetch + background refresh task every FX_REFRESH_INTERVAL_SECONDS
app.state.fx_provider = TreasuryFeedAdapter(feed_url=settings.FX_PROVIDER_URL)
await app.state.fx_provider.refresh()
asyncio.create_task(_bg_refresh_loop(app.state.fx_provider))

# Dependency injection
async def get_fx_provider(request: Request) -> FxRateProvider:
    return request.app.state.fx_provider
```

**Why not ABC**: ABC requires explicit inheritance (`class TreasuryFeedAdapter(FxRateProvider)`),
which would force a refactor of the existing `ExchangeRateService`. Protocol avoids this.

**Alternatives rejected**:

| Alternative | Reason Rejected |
|---|---|
| ABC / abstract base class | Forces inheritance on existing `ExchangeRateService`; breaks zero-change backward compat |
| Concrete class with `if settings.USE_LIVE_RATES` branch | Not swappable; tests must mock deeper; violates open/closed |
| Event-driven rate updates (Kafka/Redis) | Massively overengineered for a 60-minute refresh |

---

## Decision 2: Rate Snapshot Persistence

**Decision**: PostgreSQL `fx_rate_snapshot` table with a short in-memory read-through cache
(per-request: serve from DB, not live HTTP call).

**Rationale**:

1. **Restart survival**: Pure in-memory cache is cleared on pod restart. If the provider is
   down at startup, the service has no rates. The DB snapshot provides rates immediately.
2. **Multi-instance consistency**: All FastAPI instances read from the same PostgreSQL snapshot;
   no divergent "last updated" timestamps.
3. **DI-006 compliance**: `fx_snapshot_id` FK on `transfers` satisfies the requirement that
   *"exchange rates used in completed transactions MUST be stored immutably."*
4. **Staleness is a DB query**: `WHERE fetched_at < NOW() - INTERVAL '60 minutes'` — trivially
   expressible, visible to all instances simultaneously.
5. **Architectural consistency**: Every other queryable system state lives in PostgreSQL.

**Schema** (see `data-model.md` for full column list):
- One row per refresh; never deleted (append-only for audit).
- `is_stale` column set `True` when provider fails after retries or age exceeded.
- `rates` stored as JSONB with decimal values as strings to preserve precision.
- Index on `effective_at DESC` for fast latest-snapshot retrieval.

**Alternatives rejected**:

| Alternative | Reason Rejected |
|---|---|
| Pure in-memory TTL cache (`cachetools.TTLCache`) | Cleared on restart; divergent state across pods; violates DI-006 |
| Redis with TTL | New infrastructure dependency; PostgreSQL handles one write per 60 min easily |
| Store rate inline per transfer row only | Satisfies DI-006 per-transaction but not the rate table display or staleness check |
| Rely on provider availability | Unacceptable downtime if provider down at startup |

---

## Decision 3: Transfer State Machine Migration

**Decision**: Single additive Alembic migration (003) — rename column, add columns, extend
Python enum. No DDL type alteration needed.

**Key finding**: `transfers.status` is `VARCHAR(20)` (not a PostgreSQL native `ENUM` type).
Adding new status values (`pending`, `processing`, `failed`) is a **Python-only change** —
no DDL column type alteration, no table scan, no long lock.

**Migration 003 DDL**:
```sql
ALTER TABLE transfers RENAME COLUMN rejection_reason TO failure_reason;
ALTER TABLE transfers ADD COLUMN transfer_type VARCHAR(30) NOT NULL DEFAULT 'same_currency';
ALTER TABLE transfers ADD COLUMN sending_fee NUMERIC(19,4);
ALTER TABLE transfers ADD COLUMN sending_fee_currency CHAR(3);
ALTER TABLE transfers ADD COLUMN receiving_fee NUMERIC(19,4);
ALTER TABLE transfers ADD COLUMN receiving_fee_currency CHAR(3);
ALTER TABLE transfers ADD COLUMN fx_snapshot_id UUID REFERENCES fx_rate_snapshot(id);
ALTER TABLE transfers ADD COLUMN rate_confirmed_at TIMESTAMPTZ;
```

**Locking**: All operations acquire `ACCESS EXCLUSIVE` for milliseconds only (metadata / fast
path in PostgreSQL 11+). No table scan, no data copy. Safe for near-zero-downtime deployment.

**Python enum update** (additive, backward compatible):
```python
class TransferStatus(str, enum.Enum):
    completed = "completed"   # existing
    rejected = "rejected"     # existing (legacy, ≡ failed)
    pending = "pending"       # new
    processing = "processing" # new
    failed = "failed"         # new
```

**State transition enforcement** (service layer only, no DB constraint — consistent with
existing approach):
```
PENDING → PROCESSING → COMPLETED (terminal)
                     → FAILED    (terminal)
```
Invalid transitions raise `ValidationError`.

**Alternatives rejected**:

| Alternative | Reason Rejected |
|---|---|
| Separate `cross_currency_transfers` table | Splits transfer history; complicates audit log; duplicates idempotency logic |
| PostgreSQL native ENUM + `ALTER TYPE ADD VALUE` | Non-transactional in PG 12+; unnecessary since column is already VARCHAR |
| CHECK CONSTRAINT on status | Full table scan under lock; redundant with app-layer enforcement |

---

## Decision 4: In-App Notification Model

**Decision**: `notifications` table, written atomically within the same `session.begin()` block
as transfer completion, polled via `GET /api/v1/notifications`.

**Rationale**: Matches the existing audit log write pattern (`repositories/transfer_repository.py:62–85`).
Notifications are a mandatory side-effect of transfer completion — writing them in the same
transaction eliminates the entire class of "notification lost on crash" failures.

**Schema** (key columns):
- `user_id TEXT NOT NULL` — JWT `sub` claim of the account owner (not account_number)
- `transfer_id UUID NOT NULL` — FK to `transfers.id`
- `notification_type VARCHAR(50)` — controlled vocab: `transfer_sent`, `transfer_received`
- `metadata JSONB NOT NULL` — FR-014 payload: direction, amounts, currencies, detail link
- `is_read BOOLEAN NOT NULL DEFAULT false`
- Index: `(user_id, is_read, created_at DESC)` — primary access pattern

**Write path**: Inside the same `async with session.begin()` block as `COMPLETED` status
transition. Two rows created: one for sender (`transfer_sent`), one for recipient (`transfer_received`).

**Read path**: `GET /api/v1/notifications?unread_only=true` (polling); recommended client
cadence: on page load + every 30 seconds. `PATCH /api/v1/notifications/{id}/read` to mark read.

**Alternatives rejected**:

| Alternative | Reason Rejected |
|---|---|
| FastAPI `BackgroundTask` (post-response write) | Writes after HTTP response; notification silently lost on crash; violates atomicity |
| PostgreSQL LISTEN/NOTIFY | Still needs persistent server→client channel (WebSocket/SSE) to deliver signal |
| WebSocket / SSE | Persistent connections not in scope; no WebSocket layer in existing service |
| Separate notification microservice | Distributed transaction problem; massively overengineered for v1 |
| Email / SMS | Explicitly out of scope (spec FR-013) |

---

## Cross-Decision Integration

1. **Staleness gates transfers**: `FxRateProvider.is_stale()` (Decision 1) is checked before
   any account lock is acquired; raises `StaleRateError` immediately (Decision 3).
2. **Snapshot ID links rate to transfer**: `fx_snapshot_id` FK on `transfers` references the
   DB snapshot (Decision 2), satisfying DI-006 immutability requirement.
3. **Notifications are the last write in the completion transaction**: Only on `COMPLETED`
   state transition (Decision 3) are `Notification` rows written (Decision 4) — in the same
   `session.begin()` block, flushed before commit. If notification write fails, the entire
   transaction rolls back.
4. **Protocol makes everything testable**: Tests inject `StaticFxRateProvider` (Decision 1),
   which never returns stale — no time mocking needed. `TreasuryFeedAdapter` tested separately
   with a mocked `httpx.AsyncClient`.
