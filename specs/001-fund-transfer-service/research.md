# Research: Fund Transfer Service

**Phase**: 0 — Pre-Design Research | **Date**: 2026-06-15
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## 1. Technology Stack

### Decision: Python 3.12 + FastAPI 0.111 + SQLAlchemy 2.x async + asyncpg + PostgreSQL 16

**Rationale**:

FastAPI is the only Python framework that simultaneously delivers all service requirements:
- Auto-generated OpenAPI 3.1 spec (constitution: API-Driven Design)
- Native `async/await` for asyncpg — non-blocking DB access
- Pydantic v2 validation with `Decimal` support for monetary amounts
- `HTTPBearer` security scheme and `Security()` dependency injection for JWT
- `Depends()` for clean session/auth principal injection

**Evidence**: Production payment and banking services consistently choose FastAPI
(`LedgerKit`, `awaregh/Designing-Idempotent-APIs-at-Scale`, `j4sysiak/PythonProject-2` MiniBank).

**Alternatives considered**:

| Framework | OpenAPI | Async DB | Pydantic | Verdict |
|-----------|---------|----------|----------|---------|
| **FastAPI** | Auto-generated | Native | Built-in v2 | **Chosen** |
| Django REST | Via drf-spectacular | ASGI adapter needed | Manual serializers | Heavyweight, sync-first ORM |
| Flask | Manual / flasgger | Not async | Not built-in | Too low-level for banking |
| aiohttp | Manual | Async | Not built-in | No DI, no validation layer |
| Litestar | Auto-generated | Async | Supported | Viable; smaller ecosystem |

**SQLAlchemy 2.x chosen over raw asyncpg** for: `with_for_update()` row-level locking,
Alembic migration toolchain, and type-safe ORM queries.

---

## 2. Idempotency Pattern

### Decision: X-Idempotency-Key header + PostgreSQL dual-write, 24 h TTL

**Full Flow**:
```
POST /api/v1/transfers:
  1. Validate X-Idempotency-Key header (required, max 255 chars)
  2. SELECT idempotency_keys WHERE key = :key FOR UPDATE NOWAIT
     → If found and not expired: return stored response (HTTP 200 + X-Idempotency-Replay: true)
     → If found with different request SHA-256: return 409 Conflict
  3. INSERT idempotency_keys (key, owner_id, request_hash, status='in_progress')
     → ON CONFLICT DO NOTHING guards concurrent identical requests
  4. Execute transfer (debit + credit + audit log) in same transaction
  5. UPDATE idempotency_keys SET response_body, response_status, status='complete'
```

Note: A Redis distributed lock layer (recommended for production at high load) can be added
in front of step 2 to prevent PostgreSQL lock contention under 500+ concurrent retries.
For this service, the PostgreSQL-only approach is sufficient per spec requirements.

**Idempotency Key Table**:
```sql
CREATE TABLE idempotency_keys (
    key             VARCHAR(255)    PRIMARY KEY,
    owner_id        TEXT            NOT NULL,           -- ties key to JWT sub claim
    request_hash    VARCHAR(64)     NOT NULL,           -- SHA-256 of request body
    response_body   JSONB,
    response_status SMALLINT,
    status          VARCHAR(20)     NOT NULL DEFAULT 'in_progress', -- in_progress | complete | failed
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ     NOT NULL            -- now() + interval '24 hours'
);
CREATE INDEX idempotency_keys_expires_at_idx ON idempotency_keys (expires_at);
```

**Edge Cases**:

| Scenario | Response |
|----------|----------|
| Concurrent identical key (status=in_progress) | 409 with "Transfer in progress — retry after 1s" |
| Same key, different request body (hash mismatch) | 409 "Idempotency-Key reused with different request" |
| Same key, different owner_id | 409 "Idempotency-Key owned by different caller" |
| Key expired (expires_at < now()) | Treat as new request — re-process |
| Replay (status=complete) | 200 + X-Idempotency-Replay: true + original response body |

---

## 3. Concurrent Transfer Locking

### Decision: Pessimistic locking (SELECT FOR UPDATE) with deterministic lock ordering

**Pattern**:
```python
async with session.begin():
    # Always acquire locks in ascending account_id order — prevents A→B / B→A deadlock
    ids_ordered = sorted([from_account_id, to_account_id])
    result = await session.execute(
        select(Account)
        .where(Account.id.in_(ids_ordered))
        .order_by(Account.id)
        .with_for_update()
    )
    accounts = {acc.id: acc for acc in result.scalars().all()}
    # ... validate and apply debit/credit ...
```

**Tradeoff Analysis (at 500 concurrent transfers)**:

| Factor | Pessimistic (SELECT FOR UPDATE) | Optimistic (version column) |
|--------|----------------------------------|------------------------------|
| Correctness | Guaranteed | Correct with retry |
| No-contention throughput | Good | Excellent |
| Hot-account throughput | Predictable queue | Retry storm |
| Deadlock risk | Eliminated by ordering | None |
| Implementation complexity | Low | High (retry loop + StaleDataError) |

**Rationale**: At ≥ 10% conflict rate (expected for a settlement/clearing account),
optimistic locking causes a retry storm — all losing threads re-read and re-attempt.
Pessimistic creates a predictable queue. Production evidence (Significant-Gravitas/AutoGPT
credit.py) confirms: "After extensive analysis of concurrency patterns, we determined FOR UPDATE."

**Additional mitigations**:
- `lock_timeout = '5s'` at session level (fail-fast)
- Deadlock retry decorator: max 3 retries with exponential backoff on `DeadlockDetected`
- `NOWAIT` on idempotency key SELECT FOR UPDATE to avoid blocking on in-progress duplicates

---

## 4. Decimal Precision

### Decision: NUMERIC(19, 4) for amounts/balances; NUMERIC(20, 8) for exchange rates

**Type Mapping**:

| Layer | Type | Notes |
|-------|------|-------|
| PostgreSQL (amounts) | `NUMERIC(19, 4)` | 15 integral digits, 4 decimal places; covers all fiat currencies |
| PostgreSQL (exchange rates) | `NUMERIC(20, 8)` | Extra precision for FX rate storage (e.g., 1.08543211) |
| SQLAlchemy column | `Numeric(precision=19, scale=4, asdecimal=True)` | `asdecimal=True` returns Python `Decimal`, not float |
| Python service | `decimal.Decimal` | Exact arithmetic, no IEEE 754 rounding |
| Pydantic schema | `Decimal` | Validated: > 0, max 4 decimal places |
| JSON API response | String (`"100.0000"`) | Avoids JSON float precision loss |

**Critical rule**: NEVER use PostgreSQL `MONEY` type — locale-dependent formatting
(lc_monetary) causes asyncpg to return a locale-formatted string, not a Decimal.
NEVER use Python `float` for monetary arithmetic.

**NUMERIC(19, 4) capacity**: max ~999,999,999,999,999.9999 — covers every real-world
fiat currency balance.

---

## 5. Authentication and Authorization

### Decision: PyJWT >= 2.8 with PyJWKClient for JWKS-based JWT validation

**Pattern**:
```python
# PyJWKClient caches the JWK set in memory, re-fetches every `lifespan` seconds
jwks_client = PyJWKClient(
    JWKS_URI,
    cache_jwk_set=True,
    lifespan=3600,   # re-fetch keys every 1 hour
    timeout=10
)

def validate_token(token: str) -> dict:
    signing_key = jwks_client.get_signing_key_from_jwt(token)   # matches via 'kid'
    return decode(
        token,
        signing_key.key,
        algorithms=["RS256"],          # whitelist — rejects HS256 confusion attacks
        audience="fund-transfer-service",
        options={"verify_exp": True}
    )
```

**Authorization Rules**:
| Endpoint | Rule |
|----------|------|
| `GET /accounts/{number}` | Caller's JWT `sub` == account `owner_id` OR caller has `role=operator` |
| `POST /accounts` | Any authenticated caller |
| `DELETE /accounts/{number}` | Caller's JWT `sub` == account `owner_id` OR `role=operator` |
| `POST /transfers` | Caller's JWT `sub` == source account `owner_id` |

**Library**: `PyJWT >= 2.8` (preferred over `python-jose` which is unmaintained,
and `authlib` which is overkill for validation-only use).

---

## 6. Exchange Rate Configuration

### Decision: YAML config file loaded at startup, parsed to Decimal, immutable after startup

**YAML Structure** (`config/exchange_rates.yaml`):
```yaml
supported_currencies:
  - EUR
  - USD
  - GBP
  - CHF
  - RON

max_transfer_amounts:
  EUR: "1000000.0000"
  USD: "1000000.0000"
  GBP: "850000.0000"
  CHF: "950000.0000"
  RON: "4970000.0000"

rates:
  EUR:
    USD: "1.0850"
    GBP: "0.8550"
    CHF: "0.9450"
    RON: "4.9700"
  USD:
    EUR: "0.9217"
    GBP: "0.7880"
    CHF: "0.8710"
    RON: "4.5806"
```

**Rules**:
- Rates stored as YAML strings → parsed to `Decimal` at load time
  (YAML floats are IEEE 754 — never use them for monetary values)
- Same-currency rate is always `Decimal("1")` — not stored in config
- Config loaded once at FastAPI `lifespan` startup event; `@lru_cache` prevents re-reads
- Config validation at load time (Pydantic model): all rates > 0, all currencies in supported list

**Alternatives considered**:

| Approach | Verdict |
|----------|---------|
| Environment variables (EUR_USD=1.08) | Rejected — N×M vars, no structure, no validation |
| Python dict in settings.py | Rejected — mixed with code, harder to diff/audit |
| Database table | Rejected — overkill for static rates; adds DB read every transfer |
| **YAML file** | **Chosen** — structured, validated at startup, human-readable diffs |