# Tasks: Fund Transfer Service

**Input**: Design documents from `specs/001-fund-transfer-service/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/openapi.yaml ✅

**Tests**: Included — TDD workflow is mandated by the project constitution (Test-First Development principle confirmed in plan.md; coverage targets: unit > 95%, integration > 80%).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4, maps to spec.md)
- Exact file paths included in every description

## Path Conventions

- Source code: `src/fund_transfer/` (Python package root)
- Tests: `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/load/`
- Migrations: `alembic/versions/`
- Config: `config/`
- Infrastructure: `docker/`, project root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, directory structure, and Docker infrastructure

- [X] T001 Create full project directory structure as defined in plan.md: `src/fund_transfer/{api/v1/,api/middleware/,core/,models/,repositories/,schemas/,services/}`, `tests/{unit/,integration/,contract/,load/}`, `alembic/versions/`, `config/`, `docker/` with `__init__.py` files in all Python packages
- [X] T002 Create `pyproject.toml` with Python 3.12, all dependencies from plan.md: FastAPI 0.111, uvicorn, SQLAlchemy 2.0, asyncpg, pydantic v2, alembic, PyJWT>=2.8, structlog, prometheus-fastapi-instrumentator, opentelemetry-sdk, opentelemetry-instrumentation-fastapi, pytest, pytest-asyncio, httpx, pytest-cov, locust; configure `[tool.pytest.ini_options]` for asyncio_mode=auto
- [X] T003 [P] Create `docker/Dockerfile` for the fund-transfer service: Python 3.12-slim base, install pyproject.toml deps, copy `src/`, expose port 8000, CMD `uvicorn fund_transfer.main:app --host 0.0.0.0 --port 8000`
- [X] T004 [P] Create `docker-compose.yml` with two services: `fund-transfer-service` (built from `docker/Dockerfile`, depends on `postgres`, env_file `.env`) and `postgres` (image: postgres:16-alpine, POSTGRES_DB=fund_transfer, POSTGRES_USER, POSTGRES_PASSWORD, healthcheck with `pg_isready`)
- [X] T005 [P] Create `.env.example` with all required environment variables: `DATABASE_URL`, `JWKS_URI`, `JWT_AUDIENCE`, `EXCHANGE_RATES_CONFIG`, `LOG_LEVEL`, `SERVICE_NAME`
- [X] T006 [P] Create `config/exchange_rates.yaml` with `supported_currencies` list (EUR, USD, GBP, CHF, RON), `max_transfer_amounts` per currency as decimal strings (e.g., `"1000000.0000"`), and `rates` nested dict (from_currency → to_currency → decimal string); all rate values as YAML strings not floats

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Initialize Alembic for async PostgreSQL: run `alembic init alembic`, configure `alembic/alembic.ini` (sqlalchemy.url from env), update `alembic/env.py` to use asyncio-compatible migration runner (`run_async_migrations`) with `asyncpg` dialect and import `Base.metadata` for `target_metadata`
- [X] T008 Create `src/fund_transfer/core/config.py` using `pydantic-settings` BaseSettings: fields `DATABASE_URL`, `JWKS_URI`, `JWT_AUDIENCE`, `EXCHANGE_RATES_CONFIG` (path to YAML), `LOG_LEVEL`; add `ExchangeRateConfig` Pydantic model with `supported_currencies: list[str]`, `max_transfer_amounts: dict[str, Decimal]`, `rates: dict[str, dict[str, Decimal]]`; load YAML at startup parsing all rate values as `Decimal` (never float); `@lru_cache` on settings factory
- [X] T009 [P] Create `src/fund_transfer/core/exceptions.py` with domain exception hierarchy: base `FundTransferError`; subclasses `ValidationError` (400), `NotFoundError` (404), `ForbiddenError` (403), `InsufficientFundsError` (422), `LimitExceededError` (422), `IdempotencyConflictError` (409), `AccountHasBalanceError` (400), `DatabaseError` (500); each carries `error_code: str` and `message: str`
- [X] T010 [P] Create `src/fund_transfer/core/database.py` with async SQLAlchemy engine: `create_async_engine` with `asyncpg`, connection pool (pool_size=20, max_overflow=10), `async_sessionmaker` with `expire_on_commit=False`; declare `Base = DeclarativeBase()`; define `get_session` async generator dependency for FastAPI `Depends()`
- [X] T011 [P] Create `src/fund_transfer/core/security.py`: initialize `PyJWKClient(JWKS_URI, cache_jwk_set=True, lifespan=3600, timeout=10)`; implement `validate_token(token: str) -> dict` using `jwt.decode` with `algorithms=["RS256"]`, audience from config, `verify_exp=True`; implement `get_current_user(credentials: HTTPAuthorizationCredentials) -> dict` FastAPI dependency; add `is_operator(claims: dict) -> bool` checking `role=operator` claim
- [X] T012 [P] Create `src/fund_transfer/schemas/errors.py` with `ErrorResponse` Pydantic model: `error_code: str`, `message: str`, `request_id: str`, `details: dict | None = None`; matches OpenAPI `ErrorResponse` schema exactly
- [X] T013 [P] Create `src/fund_transfer/api/middleware/correlation.py`: Starlette middleware that reads `X-Request-ID` header (or generates UUID4 if absent), binds it to structlog context variable, and adds `X-Request-ID` to every response header
- [X] T014 [P] Create `src/fund_transfer/api/middleware/error_handler.py`: FastAPI exception handler registrations mapping each domain exception to `JSONResponse` with correct HTTP status and `ErrorResponse` body; catch-all for unhandled exceptions returns HTTP 500 with generic message (no stack trace exposed — SEC-006)
- [X] T015 [P] Create `src/fund_transfer/api/middleware/auth.py`: `get_auth_principal` dependency using `HTTPBearer` security scheme, calls `security.validate_token`, returns `claims: dict`; add `require_owner_or_operator(account_owner_id: str, claims: dict)` helper raising `ForbiddenError` if `claims["sub"] != account_owner_id` and not `is_operator(claims)`
- [X] T016 Create `src/fund_transfer/main.py`: `create_app()` factory returning FastAPI with title="Fund Transfer Service", version="1.0.0"; register `CorrelationMiddleware`; register all exception handlers from `error_handler.py`; add lifespan context manager (load exchange rate config at startup, dispose DB engine at shutdown); include `api_router` at prefix `/api/v1`; add `prometheus-fastapi-instrumentator` instrumentation; add OpenTelemetry `FastAPIInstrumentor`; add `GET /health` returning `{"status": "ok"}`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Create a New Account (Priority: P1) 🎯 MVP

**Goal**: Allow any authenticated caller to create a financial account with a unique account number, validated currency, and exact opening balance

**Independent Test**: Submit `POST /api/v1/accounts` with valid owner, currency, and opening balance → verify HTTP 201 with unique `account_number` matching `ACCT-[A-Z0-9]{12}` pattern and `balance` equal to `opening_balance`

### Tests for User Story 1 (TDD — write FIRST, verify they FAIL, then implement)

- [X] T017 [P] [US1] Write unit tests for account creation service in `tests/unit/test_account_service.py`: test valid EUR account created with correct balance; test negative opening balance raises `ValidationError`; test unsupported currency raises `ValidationError`; test generated account_number matches `ACCT-[A-Z0-9]{12}` pattern and is unique across 1000 calls; mock repository and exchange_rate_service
- [X] T018 [P] [US1] Write contract tests for `POST /api/v1/accounts` in `tests/contract/test_accounts_create.py` using httpx async client: HTTP 201 with `AccountResponse` schema (account_number, owner_id, currency, balance as decimal string, status="active"); HTTP 400 `VALIDATION_ERROR` for negative opening_balance; HTTP 400 `UNSUPPORTED_CURRENCY` for unknown currency code; HTTP 400 for missing required fields (owner_id, currency); HTTP 401 for missing JWT
- [X] T019 [P] [US1] Write integration tests for account creation full DB round-trip in `tests/integration/test_accounts_create.py`: account persisted and immediately queryable; `balance` in DB matches `opening_balance` exactly as `Decimal`; audit log entry with `operation_type="account_created"` written in same transaction; duplicate request with same idempotency key (if header provided) returns same response

### Implementation for User Story 1

- [X] T020 [P] [US1] Create `src/fund_transfer/models/account.py`: `Account` SQLAlchemy ORM model mapping to `accounts` table — columns: `id` UUID PK, `account_number` VARCHAR(34) UNIQUE NOT NULL, `owner_id` TEXT NOT NULL, `currency` CHAR(3) NOT NULL, `balance` Numeric(19,4,asdecimal=True) NOT NULL, `status` VARCHAR(20) NOT NULL default "active", `owner_pii_hash` VARCHAR(64), `created_at` TIMESTAMPTZ server_default=now(), `updated_at` TIMESTAMPTZ onupdate=now(); define `AccountStatus` enum; add all indexes from data-model.md
- [X] T021 [P] [US1] Create `src/fund_transfer/models/audit_log.py`: `AuditLogEntry` SQLAlchemy ORM model mapping to `audit_log` table — columns: `id` UUID PK, `operation_type` VARCHAR(30) NOT NULL, `actor_identity` TEXT NOT NULL, `affected_account_numbers` ARRAY(TEXT) NOT NULL, `amount` Numeric(19,4) nullable, `currency` CHAR(3) nullable, `outcome` VARCHAR(20) NOT NULL, `detail` JSONB nullable, `timestamp` TIMESTAMPTZ server_default=now(), `request_id` TEXT nullable; define `OperationType` enum; add GIN index on `affected_account_numbers` and all indexes from data-model.md
- [X] T022 [US1] Create Alembic migration for `accounts` and `audit_log` tables in `alembic/versions/`: `accounts` with all columns and `NUMERIC(19,4)` for balance; `audit_log` with `TEXT[]` for `affected_account_numbers`, `JSONB` for detail; all indexes from data-model.md; migration must be reversible (downgrade drops tables)
- [X] T023 [P] [US1] Create `src/fund_transfer/schemas/account.py`: `CreateAccountRequest` Pydantic model with `owner_id: str` (minLen=1, maxLen=255), `currency: str` (len=3, uppercase), `opening_balance: Decimal` (≥0, max 4 decimal places); `AccountResponse` Pydantic model with all fields from OpenAPI `AccountResponse` schema — serialize `balance` as string with 4 decimal places; `AccountStatus` enum
- [X] T024 [US1] Create `src/fund_transfer/repositories/account_repository.py` with `AccountRepository` class taking `AsyncSession`: `create(owner_id, currency, balance, actor_identity, request_id) -> Account` — generate `ACCT-<12 alphanum>` account_number (retry on conflict), INSERT account and INSERT audit_log entry in same transaction; `get_by_account_number(account_number) -> Account | None`
- [X] T025 [US1] Create `src/fund_transfer/services/exchange_rate_service.py`: `ExchangeRateService` loaded from `ExchangeRateConfig`; `validate_currency(code: str)` raises `ValidationError` if not in supported_currencies; `get_rate(from_currency: str, to_currency: str) -> Decimal` returns `Decimal("1")` for same currency, config rate for cross-currency, raises `ValidationError` for unsupported pair; `get_max_transfer_amount(currency: str) -> Decimal`
- [X] T026 [US1] Create `src/fund_transfer/services/account_service.py` with `AccountService`: `create_account(request: CreateAccountRequest, actor_identity: str, request_id: str, session: AsyncSession) -> AccountResponse` — validate currency via `ExchangeRateService.validate_currency`; validate `opening_balance >= 0`; call `AccountRepository.create`; return `AccountResponse`
- [X] T027 [US1] Create `src/fund_transfer/api/v1/accounts.py`: `POST /accounts` endpoint — `auth_principal: dict = Depends(get_auth_principal)`, `request: CreateAccountRequest`, inject `AsyncSession`; call `account_service.create_account`; return HTTP 201 with `AccountResponse`; include `X-Request-ID` response header
- [X] T028 [US1] Create `src/fund_transfer/api/v1/router.py`: define `api_router = APIRouter(prefix="/api/v1")`; include accounts router (tag="Accounts"); placeholder import for transfers router (to be added in T045)

**Checkpoint**: US1 is fully functional — `POST /api/v1/accounts` returns unique account numbers with exact balances. All unit, contract, and integration tests must pass.

---

## Phase 4: User Story 2 — Retrieve Account Balance (Priority: P1)

**Goal**: Allow authorized callers to retrieve the exact current balance and metadata for any account they own

**Independent Test**: Create an account (US1), then call `GET /api/v1/accounts/{account_number}` → HTTP 200 with `balance` exactly matching the opening balance; call with nonexistent number → HTTP 404

### Tests for User Story 2 (TDD — write FIRST, verify they FAIL, then implement)

- [X] T029 [P] [US2] Write unit tests for account retrieval service in `tests/unit/test_account_service_read.py`: test found account returns correct fields; test nonexistent account_number raises `NotFoundError`; test closed account raises `NotFoundError`; test caller with matching JWT sub can retrieve own account; test caller with mismatched JWT sub raises `ForbiddenError` unless `is_operator`; mock repository
- [X] T030 [P] [US2] Write contract tests for `GET /api/v1/accounts/{account_number}` in `tests/contract/test_accounts_get.py`: HTTP 200 full `AccountResponse` schema; HTTP 404 with `ACCOUNT_NOT_FOUND` error_code for nonexistent account; HTTP 403 `FORBIDDEN` when JWT sub does not match owner and not operator; HTTP 401 for missing JWT
- [X] T031 [P] [US2] Write integration tests for balance retrieval in `tests/integration/test_accounts_get.py`: newly created account immediately queryable; `balance` field is exact decimal match; account after transfers reflects updated balance; closed account returns 404

### Implementation for User Story 2

- [X] T032 [US2] Add `get_active_by_account_number(account_number: str) -> Account` to `src/fund_transfer/repositories/account_repository.py`: SELECT where account_number matches AND status='active'; raise `NotFoundError(error_code="ACCOUNT_NOT_FOUND")` if not found or closed
- [X] T033 [US2] Add `get_account(account_number: str, actor_identity: str, claims: dict, session: AsyncSession) -> AccountResponse` to `src/fund_transfer/services/account_service.py`: call `repository.get_active_by_account_number`; call `require_owner_or_operator(account.owner_id, claims)` raising `ForbiddenError` if unauthorized; return `AccountResponse`
- [X] T034 [US2] Add `GET /accounts/{account_number}` endpoint to `src/fund_transfer/api/v1/accounts.py`: path parameter `account_number: str`, `auth_principal: dict = Depends(get_auth_principal)`, inject `AsyncSession`; call `account_service.get_account`; return HTTP 200 `AccountResponse` with `X-Request-ID` header

**Checkpoint**: US1 + US2 independently functional — account creation and retrieval both work end-to-end with authorization enforcement.

---

## Phase 5: User Story 3 — Transfer Funds Between Accounts (Priority: P1)

**Goal**: Allow authorized callers to atomically transfer funds between accounts, with full idempotency, multi-currency support, transfer limits, and immutable audit logging

**Independent Test**: Create two EUR accounts; call `POST /api/v1/transfers`; verify source balance decreases and destination balance increases by exact transfer amount; verify total balance conserved; verify duplicate request with same `X-Idempotency-Key` returns original response without re-executing

### Tests for User Story 3 (TDD — write FIRST, verify they FAIL, then implement)

- [X] T035 [P] [US3] Write unit tests for transfer service in `tests/unit/test_transfer_service.py`: valid same-currency transfer: source_balance decreases by amount, dest_balance increases by amount; cross-currency: destination_amount = source_amount × exchange_rate (Decimal precision); insufficient funds raises `InsufficientFundsError`; amount > per-currency limit raises `LimitExceededError`; zero/negative amount raises `ValidationError`; self-transfer (same account) raises `ValidationError`; idempotency replay returns stored response without DB writes; mock repository and exchange_rate_service
- [X] T036 [P] [US3] Write unit tests for exchange rate service in `tests/unit/test_exchange_rate_service.py`: same-currency returns `Decimal("1")`; EUR→USD returns configured rate as `Decimal`; unsupported pair raises `ValidationError`; all rates loaded as `Decimal` not `float`; `get_max_transfer_amount` returns correct per-currency limit as `Decimal`
- [X] T037 [P] [US3] Write contract tests for `POST /api/v1/transfers` in `tests/contract/test_transfers_create.py`: HTTP 201 with full `TransferResponse` schema for same-currency; HTTP 201 with correct `exchange_rate` (8 decimal places) and `destination_amount` for cross-currency; HTTP 422 `INSUFFICIENT_FUNDS` with balances unchanged; HTTP 422 `TRANSFER_LIMIT_EXCEEDED`; HTTP 409 `IDEMPOTENCY_CONFLICT` for reused key with different body; HTTP 404 `ACCOUNT_NOT_FOUND` for nonexistent source; HTTP 400 `VALIDATION_ERROR` for zero amount; HTTP 200 with `X-Idempotency-Replay: true` for duplicate request
- [X] T038 [P] [US3] Write integration tests for fund transfers in `tests/integration/test_transfers.py`: source balance decreases by source_amount; destination balance increases by destination_amount; total combined balance conserved for same-currency; cross-currency: rate and amounts recorded in transfer record and audit log; concurrent transfers on same source account serialize without corruption or deadlock (run 10 concurrent tasks); duplicate idempotency key returns identical response, balance unchanged after second call

### Implementation for User Story 3

- [X] T039 [P] [US3] Create `src/fund_transfer/models/transfer.py`: `Transfer` ORM model mapping to `transfers` table — all fields from data-model.md; `id` UUID PK, `idempotency_key` VARCHAR(255) UNIQUE NOT NULL, source/destination account_number VARCHAR(34), `source_amount`/`destination_amount` Numeric(19,4), `exchange_rate` Numeric(20,8,asdecimal=True), `status` VARCHAR(20), `rejection_reason` TEXT nullable, `caller_id` TEXT NOT NULL, `created_at` TIMESTAMPTZ immutable server_default; define `TransferStatus` enum; add all indexes from data-model.md
- [X] T040 [US3] Create Alembic migration for `transfers` and `idempotency_keys` tables in `alembic/versions/`: `transfers` with UNIQUE on `idempotency_key`, NUMERIC(19,4) for amounts, NUMERIC(20,8) for exchange_rate, all indexes; `idempotency_keys` table with `expires_at` index; migration reversible with downgrade
- [X] T041 [P] [US3] Create `src/fund_transfer/schemas/transfer.py`: `CreateTransferRequest` Pydantic model with `source_account_number: str`, `destination_account_number: str`, `amount: Decimal` (>0, max 4 decimal places); validator: source != destination; `TransferResponse` Pydantic model matching OpenAPI contract — `exchange_rate` serialized as 8-decimal string, all amounts as 4-decimal strings
- [X] T042 [US3] Create `src/fund_transfer/repositories/transfer_repository.py` with `TransferRepository`: `get_idempotency_record(key, session) -> idempotency_keys row | None` using SELECT FOR UPDATE NOWAIT (raises `IdempotencyConflictError` on lock contention); `create_idempotency_lock(key, owner_id, request_hash, session)` using INSERT ON CONFLICT DO NOTHING; `create_transfer(transfer_data, session) -> Transfer`; `complete_idempotency(key, response_body, response_status, session)`; `get_transfer_replay(key, session) -> dict` returning stored response_body
- [X] T043 [US3] Create `src/fund_transfer/services/transfer_service.py` with `TransferService.execute_transfer(request, caller_id, idempotency_key, request_hash, request_id, session) -> tuple[TransferResponse, bool]` — (1) validate amount > 0 and not self-transfer; (2) check idempotency: if complete replay stored response; if in_progress raise 409; (3) insert idempotency lock; (4) acquire account locks via `SELECT FOR UPDATE` ordered by UUID ascending (deadlock prevention); (5) validate both accounts active, source balance >= amount, amount <= per-currency limit; (6) get exchange rate; (7) compute destination_amount = source_amount × rate (Decimal); (8) debit source, credit destination; (9) INSERT transfer record; (10) INSERT audit_log entry; (11) UPDATE idempotency key to complete — all steps (4)–(11) within single `async with session.begin()` transaction
- [X] T044 [US3] Create `src/fund_transfer/api/v1/transfers.py`: `POST /transfers` endpoint — `x_idempotency_key: str = Header(alias="X-Idempotency-Key", min_length=1, max_length=255)`, `auth_principal: dict = Depends(get_auth_principal)`, `request: CreateTransferRequest`, inject `AsyncSession`; compute SHA-256 of request body for idempotency hash; call `transfer_service.execute_transfer`; return HTTP 201 (new) or HTTP 200 (replay) `TransferResponse` with `X-Idempotency-Replay` header and `X-Request-ID` header
- [X] T045 [US3] Update `src/fund_transfer/api/v1/router.py` to include transfers router from `src/fund_transfer/api/v1/transfers.py` with tag="Transfers"

**Checkpoint**: US1 + US2 + US3 all independently functional — full fund transfer lifecycle works end-to-end with ACID guarantees, idempotency, and audit trail.

---

## Phase 6: User Story 4 — Delete an Account (Priority: P2)

**Goal**: Allow authorized operators or account owners to close an account with zero balance, anonymizing PII per GDPR while retaining all audit and transfer history

**Independent Test**: Create a zero-balance account; call `DELETE /api/v1/accounts/{account_number}` → HTTP 204; subsequent `GET` on same account → HTTP 404; audit log entry for deletion persists in DB

### Tests for User Story 4 (TDD — write FIRST, verify they FAIL, then implement)

- [X] T046 [P] [US4] Write unit tests for account deletion service in `tests/unit/test_account_service_delete.py`: zero-balance account deleted successfully; non-zero balance raises `AccountHasBalanceError`; nonexistent account raises `NotFoundError`; after deletion `owner_id` in DB is anonymized (SHA-256 hash, not original value); `owner_pii_hash` set correctly; audit log entry written with `operation_type="account_deleted"` in same transaction; unauthorized caller raises `ForbiddenError`; mock repository
- [X] T047 [P] [US4] Write contract tests for `DELETE /api/v1/accounts/{account_number}` in `tests/contract/test_accounts_delete.py`: HTTP 204 No Content for zero-balance account; HTTP 400 `ACCOUNT_HAS_BALANCE` for account with non-zero balance; HTTP 404 `ACCOUNT_NOT_FOUND` for nonexistent account; HTTP 403 `FORBIDDEN` for unauthorized caller; HTTP 401 for missing JWT
- [X] T048 [P] [US4] Write integration tests for account deletion in `tests/integration/test_accounts_delete.py`: deleted account returns HTTP 404 on subsequent GET; transfer records referencing deleted account are retained in DB; audit_log entries for the account are not modified; `owner_id` in accounts table is anonymized after deletion; attempt to transfer from deleted account returns 404

### Implementation for User Story 4

- [X] T049 [US4] Add `delete_account(account_number: str, actor_identity: str, request_id: str, session: AsyncSession)` to `src/fund_transfer/repositories/account_repository.py`: SELECT account FOR UPDATE; raise `NotFoundError` if not found or already closed; raise `AccountHasBalanceError` if balance != 0; SET status='closed', anonymize owner_id to SHA-256 hash, set owner_pii_hash; INSERT audit_log entry with operation_type="account_deleted"; all in single transaction
- [X] T050 [US4] Add `delete_account(account_number: str, actor_identity: str, claims: dict, request_id: str, session: AsyncSession)` to `src/fund_transfer/services/account_service.py`: fetch account; call `require_owner_or_operator(account.owner_id, claims)` raising `ForbiddenError`; delegate to `repository.delete_account`
- [X] T051 [US4] Add `DELETE /accounts/{account_number}` endpoint to `src/fund_transfer/api/v1/accounts.py`: `auth_principal: dict = Depends(get_auth_principal)`, path param `account_number: str`, inject `AsyncSession`; call `account_service.delete_account`; return HTTP 204 No Content with `X-Request-ID` header

**Checkpoint**: Full CRUD lifecycle complete — create, read, transfer, and delete all independently functional. All four user stories testable end-to-end.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Observability, performance validation, security hardening, and operational readiness

- [X] T052 [P] Update `src/fund_transfer/main.py`: add `GET /health` endpoint with async DB ping (`SELECT 1`) returning `{"status": "ok", "db": "ok"}` or `{"status": "degraded", "db": "error"}` on failure; configure `prometheus-fastapi-instrumentator` with custom metrics: `fund_transfer_transfers_total` counter (by status), `fund_transfer_active_db_connections` gauge; expose `/metrics` endpoint
- [X] T053 [P] Configure structlog structured JSON logging in `src/fund_transfer/core/config.py`: set up `structlog.configure` with `JSONRenderer`, bind `service_name` and `log_level` globally; update `CorrelationMiddleware` in `src/fund_transfer/api/middleware/correlation.py` to bind `request_id` into structlog context; add structured log statements in all service methods capturing `operation`, `actor`, `outcome`, and relevant account/transfer IDs
- [X] T054 [P] Add OpenTelemetry distributed tracing setup in `src/fund_transfer/main.py`: configure `TracerProvider` with OTLP exporter (env-configurable endpoint); instrument with `FastAPIInstrumentor`; propagate `traceparent` header; bind trace_id to structlog context for correlation
- [X] T055 [P] Create `tests/load/locustfile.py` with Locust load test scenarios targeting `http://localhost:8000`: `AccountUser` task set — create account (weight 1), retrieve balance (weight 3); `TransferUser` task set — create two accounts then transfer between them (weight 2); configure for 500 concurrent users, spawn rate 50/s; add assertions: p95 GET < 500ms, p95 POST < 2s, error rate < 1% (PERF-001, PERF-002, PERF-003)
- [X] T056 [P] Configure security scanning in `pyproject.toml`: add `[tool.bandit]` section targeting `src/fund_transfer/` with severity HIGH; create `.github/workflows/ci.yml` with jobs: `lint` (ruff/flake8), `test` (pytest with coverage thresholds: unit ≥ 95%, integration ≥ 80%), `security` (bandit + safety check); all jobs run on push and pull_request to master
- [X] T057 [P] Add deadlock retry decorator in `src/fund_transfer/services/transfer_service.py`: `@retry_on_deadlock(max_retries=3, backoff_factor=0.1)` decorator catching `asyncpg.DeadlockDetectedError` with exponential backoff; set `lock_timeout='5s'` at session level before acquiring locks; document in code why lock ordering (ascending UUID) prevents A→B / B→A deadlocks
- [X] T058 Run end-to-end validation using all scenarios from `specs/001-fund-transfer-service/quickstart.md` against live `docker-compose up` environment: Scenario 1 (create account), Scenario 2 (retrieve balance), Scenario 3 (transfer including idempotency and limit scenarios), Scenario 4 (delete account); all scenarios must pass; run `pytest tests/ -v --cov=src/fund_transfer` and verify coverage thresholds met

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; all T001–T006 can run in parallel
- **Foundational (Phase 2)**: Requires Setup (Phase 1) complete; T007 must run before T010 (Alembic before engine config); T008 before T011 (config before security); T016 last (app factory needs all middleware and security)
- **User Stories (Phase 3+)**: All depend on Foundational (Phase 2) completion
  - US1 (Phase 3) must complete before US2 (Phase 4) and US4 (Phase 6) can begin (Account model and repository shared)
  - US2 (Phase 4) and US3 (Phase 5) can proceed in parallel after Phase 3 checkpoint
  - US4 (Phase 6) depends on US1 (Account model/repo) and US3 (to drain balance via transfer in tests)
- **Polish (Phase 7)**: Requires all user stories complete; all T052–T058 are largely independent and can run in parallel

### User Story Dependencies

- **US1 (Phase 3)**: Depends only on Phase 2 — no other story dependency
- **US2 (Phase 4)**: Depends on Phase 2 + US1 (shares Account model and repository); implementation is additive (new methods on existing files)
- **US3 (Phase 5)**: Depends on Phase 2 + US1 (needs Account model for balance operations); independently testable
- **US4 (Phase 6)**: Depends on Phase 2 + US1 (Account model/repository); integration tests use US3 (transfer to drain balance)

### Within Each User Story

1. Tests written FIRST (TDD) and verified to FAIL before implementation
2. ORM models before repositories
3. Repositories before services
4. Services before API endpoints
5. Story complete and checkpointed before beginning next priority

### Parallel Opportunities

- Phase 1: T002, T003, T004, T005, T006 all in parallel after T001
- Phase 2: T008–T015 all in parallel; T007 and T016 bookend the phase
- Phase 3 tests: T017, T018, T019 in parallel; models T020, T021, T023 in parallel
- Phase 4 tests: T029, T030, T031 in parallel
- Phase 5 tests: T035, T036, T037, T038 in parallel; T039, T041 in parallel with tests
- Phase 6 tests: T046, T047, T048 in parallel
- Phase 7: T052, T053, T054, T055, T056, T057 in parallel

---

## Parallel Example: User Story 3

```bash
# Step 1 — Write tests in parallel (all different files, no dependencies):
Task: "Unit tests for transfer service in tests/unit/test_transfer_service.py"       # T035
Task: "Unit tests for exchange rate service in tests/unit/test_exchange_rate_service.py" # T036
Task: "Contract tests for POST /api/v1/transfers in tests/contract/test_transfers_create.py" # T037
Task: "Integration tests for fund transfers in tests/integration/test_transfers.py"  # T038

# Step 2 — Create model and schema in parallel (different files):
Task: "Transfer ORM model in src/fund_transfer/models/transfer.py"  # T039
Task: "Transfer Pydantic schemas in src/fund_transfer/schemas/transfer.py"  # T041

# Step 3 — Sequential: migration → repository → service → endpoint:
Task: "Alembic migration for transfers + idempotency_keys"  # T040
Task: "TransferRepository in src/fund_transfer/repositories/transfer_repository.py"  # T042
Task: "TransferService in src/fund_transfer/services/transfer_service.py"  # T043
Task: "POST /transfers endpoint in src/fund_transfer/api/v1/transfers.py"  # T044
Task: "Update router.py to include transfers router"  # T045
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T006)
2. Complete Phase 2: Foundational (T007–T016) ← **CRITICAL: blocks all stories**
3. Complete Phase 3: User Story 1 — Create Account (T017–T028)
4. **STOP and VALIDATE**: `POST /api/v1/accounts` returns 201 with unique account number
5. Deploy/demo MVP

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Phase 3) → Account creation live → **Demo: create account**
3. US2 (Phase 4) → Balance retrieval live → **Demo: create + query balance**
4. US3 (Phase 5) → Fund transfers live → **Demo: full transfer lifecycle**
5. US4 (Phase 6) → Account closure live → **Demo: full CRUD**
6. Phase 7 → Production-hardened → **Deploy: observable, secure, load-tested**

### Parallel Team Strategy

With multiple developers, after Phase 2 completes:
- **Developer A**: US1 (T017–T028) — Account creation
- Once US1 merges:
  - **Developer B**: US2 (T029–T034) — Balance retrieval (additive to accounts.py)
  - **Developer C**: US3 (T035–T045) — Fund transfers (new transfers.py)
- **Developer D**: US4 (T046–T051) after US1 merges (additive to accounts.py)

---

## Notes

- **[P]** tasks = different files, no blocking dependencies on incomplete tasks in this phase
- **[Story]** label maps each task to a specific user story for traceability and independent delivery
- All monetary values use `decimal.Decimal` in Python and `NUMERIC(19,4)` / `NUMERIC(20,8)` in PostgreSQL — never `float`
- Tests must be written and confirmed FAILING before implementation begins (TDD mandate)
- Idempotency key must be validated on all `POST /transfers` calls — not optional
- Account number generation format: `ACCT-<12 uppercase alphanumeric>` — validate uniqueness with DB retry on conflict
- All balance-modifying operations (create with opening balance, transfer debit+credit, delete) must occur within a single ACID transaction including the audit log write
- Lock ordering for transfers: acquire account locks in ascending UUID order to prevent A→B / B→A deadlocks
- Stop at each checkpoint to validate the user story works independently before proceeding
