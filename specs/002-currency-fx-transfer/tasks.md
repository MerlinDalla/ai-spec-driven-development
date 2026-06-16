# Tasks: Currency Conversion & Cross-Currency Transfer

**Input**: Design documents from `specs/002-currency-fx-transfer/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Per Constitution Principle IV (Test-First Development), tests are MANDATORY for all banking functionality. Tests MUST be written before implementation and verified to FAIL before coding begins.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story this task belongs to (US1, US2, US3)
- Exact file paths included in every task description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend the existing `fund_transfer` service with new configuration, exceptions, and module skeletons.

- [ ] T001 Add new settings to `src/fund_transfer/core/config.py`: `FX_PROVIDER_URL`, `FX_RATE_MAX_AGE_MINUTES` (default 60), `FX_RATE_DEVIATION_THRESHOLD_PCT` (default 1), `FX_REFRESH_INTERVAL_SECONDS` (default 3600), `USE_STATIC_RATES` (bool, default False for local dev fallback)
- [ ] T002 [P] Add new domain exceptions to `src/fund_transfer/core/exceptions.py`: `StaleRateError` (HTTP 503), `RateDeviationError` (HTTP 409, includes preview_rate/current_rate/deviation_pct/new_snapshot_id), `UnsupportedCurrencyPairError` (HTTP 422)
- [ ] T003 [P] Create empty module files: `src/fund_transfer/services/fx_rate_provider.py`, `src/fund_transfer/services/fx_rate_service.py`, `src/fund_transfer/services/cross_currency_transfer_service.py`, `src/fund_transfer/services/notification_service.py`, `src/fund_transfer/repositories/fx_rate_repository.py`, `src/fund_transfer/repositories/notification_repository.py`, `src/fund_transfer/schemas/fx.py`, `src/fund_transfer/schemas/notification.py`, `src/fund_transfer/api/v1/fx.py`, `src/fund_transfer/api/v1/notifications.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database migrations, new ORM models, and FX provider infrastructure — MUST complete before any user story.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Write Alembic migration `alembic/versions/003_cross_currency_transfer.py`: rename `transfers.rejection_reason` → `failure_reason`; add columns `transfer_type VARCHAR(30) NOT NULL DEFAULT ''same_currency''`, `sending_fee NUMERIC(19,4)`, `sending_fee_currency CHAR(3)`, `receiving_fee NUMERIC(19,4)`, `receiving_fee_currency CHAR(3)`, `fx_snapshot_id UUID`, `rate_confirmed_at TIMESTAMPTZ`; create `fx_rate_snapshot` table (id UUID PK, effective_at TIMESTAMPTZ server_default, fetched_at TIMESTAMPTZ server_default, is_stale BOOLEAN NOT NULL DEFAULT false, provider_source VARCHAR(100) NOT NULL, rates JSONB NOT NULL); create index `idx_fx_rate_snapshot_effective_at` on `(effective_at DESC)`; create `currency_pairs` table (id UUID PK, from_currency CHAR(3) NOT NULL, to_currency CHAR(3) NOT NULL, is_active BOOLEAN NOT NULL DEFAULT true, created_at TIMESTAMPTZ server_default); add unique constraint on `(from_currency, to_currency)`; create `notifications` table (id UUID PK, user_id TEXT NOT NULL, transfer_id UUID NOT NULL REFERENCES transfers(id), notification_type VARCHAR(50) NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, metadata JSONB NOT NULL, is_read BOOLEAN NOT NULL DEFAULT false, created_at TIMESTAMPTZ server_default); create index `idx_notifications_user_unread` on `(user_id, is_read, created_at DESC)`; add new `OperationType` enum values to `audit_log` vocabulary: `fx_rate_refreshed`, `cross_currency_transfer_initiated`, `cross_currency_transfer_completed`, `cross_currency_transfer_failed`, `notification_delivered` — documented in module before implementation
- [ ] T005 [P] Create `FxRateSnapshot` ORM model in `src/fund_transfer/models/fx_rate_snapshot.py`: fields id (UUID PK), effective_at (TIMESTAMPTZ server_default), fetched_at (TIMESTAMPTZ server_default), is_stale (Boolean), provider_source (String(100)), rates (JSONB); index on effective_at DESC
- [ ] T006 [P] Create `CurrencyPair` ORM model in `src/fund_transfer/models/currency_pair.py`: fields id (UUID PK), from_currency (CHAR(3)), to_currency (CHAR(3)), is_active (Boolean default True), created_at (TIMESTAMPTZ server_default); UniqueConstraint on (from_currency, to_currency)
- [ ] T007 [P] Create `Notification` ORM model in `src/fund_transfer/models/notification.py`: fields id (UUID PK), user_id (Text), transfer_id (UUID FK → transfers.id), notification_type (String(50)), title (Text), body (Text), metadata (JSONB), is_read (Boolean default False), created_at (TIMESTAMPTZ server_default); index on (user_id, is_read, created_at DESC)
- [ ] T008 [P] Update `Transfer` ORM model in `src/fund_transfer/models/transfer.py`: add `TransferStatus` enum values `pending`, `processing`, `failed`; rename `rejection_reason` → `failure_reason`; add mapped columns `transfer_type` (String(30)), `sending_fee` (Numeric(19,4), nullable), `sending_fee_currency` (CHAR(3), nullable), `receiving_fee` (Numeric(19,4), nullable), `receiving_fee_currency` (CHAR(3), nullable), `fx_snapshot_id` (UUID, nullable), `rate_confirmed_at` (TIMESTAMPTZ, nullable)
- [ ] T009 [P] Update `OperationType` enum in `src/fund_transfer/models/audit_log.py`: add values `fx_rate_refreshed`, `cross_currency_transfer_initiated`, `cross_currency_transfer_completed`, `cross_currency_transfer_failed`, `notification_delivered`
- [ ] T010 Import new models in `alembic/env.py` so Alembic detects them: `FxRateSnapshot`, `CurrencyPair`, `Notification`
- [ ] T011 Define `RateSnapshot` frozen dataclass and `FxRateProvider` Protocol (with `@runtime_checkable`) in `src/fund_transfer/services/fx_rate_provider.py`: async methods `get_rate(from_currency, to_currency) -> Decimal`, `get_snapshot() -> RateSnapshot`, `is_stale() -> bool`, `refresh() -> None`; sync method `validate_currency(code) -> None`
- [ ] T012 [P] Implement `StaticFxRateProvider` in `src/fund_transfer/services/fx_rate_provider.py`: wraps existing `ExchangeRateConfig`; `is_stale()` always returns `False`; `refresh()` is a no-op; satisfies `FxRateProvider` Protocol without inheriting from it
- [ ] T013 [P] Implement `TreasuryFeedAdapter` in `src/fund_transfer/services/fx_rate_provider.py`: async `httpx.AsyncClient` with 5 s connect timeout, 15 s read timeout; 2 retries with exponential backoff; `asyncio.Lock` to prevent thundering herd on concurrent refresh; marks snapshot stale after 3 consecutive failures; parses JSON response into `RateSnapshot`
- [ ] T014 Wire `FxRateProvider` into FastAPI lifespan in `src/fund_transfer/main.py`: instantiate `TreasuryFeedAdapter` (or `StaticFxRateProvider` if `USE_STATIC_RATES=True`) at startup; call `await provider.refresh()`; assign to `app.state.fx_provider`; launch `asyncio.create_task` background loop that refreshes every `FX_REFRESH_INTERVAL_SECONDS`; add `get_fx_provider(request: Request) -> FxRateProvider` FastAPI dependency
- [ ] T015 [P] Implement `FxRateRepository` in `src/fund_transfer/repositories/fx_rate_repository.py`: `get_latest_snapshot(session) -> FxRateSnapshot | None`; `insert_snapshot(session, rates_dict, provider_source) -> FxRateSnapshot`; `mark_stale(session, snapshot_id) -> None`; `get_active_currency_pairs(session) -> list[CurrencyPair]`; all methods use `async with session` pattern consistent with existing repositories
- [ ] T016 [P] Implement `NotificationRepository` in `src/fund_transfer/repositories/notification_repository.py`: `create_notifications(session, sender_notif, recipient_notif) -> None` (flush inside caller's session.begin()); `list_for_user(session, user_id, unread_only) -> list[Notification]`; `mark_read(session, notification_id, user_id) -> Notification`; enforces owner check in `mark_read`

**Checkpoint**: Migration ready, all ORM models defined, FX provider wired — user story phases can begin.

---

## Phase 3: User Story 1 — View Live Exchange Rates (Priority: P1) 🎯 MVP

**Goal**: Authenticated customers can view the current exchange rate table (buy/sell rates, last-updated timestamp, staleness flag) and preview a currency conversion with split fees.

**Independent Test**: Navigate to `GET /api/v1/fx/rates`, verify rates are shown with `is_stale: false` and a recent `effective_at`. Call `POST /api/v1/fx/convert` with 100 EUR → USD and verify `estimated_net_amount`, `sending_fee`, `receiving_fee`, and `snapshot_id` are all present.

### Tests for User Story 1 (MANDATORY — TDD, write FIRST, verify FAIL before implementing)

> **Per Constitution Principle IV**: Tests MUST fail before implementation begins. FX math requires >95% unit test coverage.

- [ ] T017 [P] [US1] Write contract test for `GET /api/v1/fx/rates` (200 with rate table, 401 without auth) in `tests/contract/test_fx_rates.py`
- [ ] T018 [P] [US1] Write contract test for `POST /api/v1/fx/convert` (200 with preview including all fee fields, 422 for unsupported pair, 503 for stale rates) in `tests/contract/test_fx_rates.py`
- [ ] T019 [P] [US1] Write unit tests for `FxRateService`: staleness detection, rate lookup via snapshot, fee preview calculation (sending_fee, receiving_fee, net_amount, total_sender_cost), rounding (half-up per ISO 4217), unsupported pair error in `tests/unit/test_fx_rate_service.py`
- [ ] T020 [P] [US1] Write unit tests for `FxRateProvider` implementations: `StaticFxRateProvider.is_stale()` always False, `TreasuryFeedAdapter` with mocked `httpx.AsyncClient` (success, timeout, retry, stale-after-3-failures) in `tests/unit/test_fx_rate_provider.py`

### Implementation for User Story 1

- [ ] T021 [P] [US1] Create FX schemas in `src/fund_transfer/schemas/fx.py`: `ExchangeRateSchema`, `RateTableResponse` (snapshot_id, effective_at, is_stale, rates list), `ConversionPreviewRequest` (from_currency, to_currency, amount), `ConversionPreviewResponse` (all fee fields from OpenAPI contract: input_amount, exchange_rate, gross_converted_amount, estimated_sending_fee, estimated_receiving_fee, estimated_net_amount, total_sender_cost, snapshot_id, effective_at, is_stale)
- [ ] T022 [US1] Implement `FxRateService` in `src/fund_transfer/services/fx_rate_service.py`: `get_rate_table(session) -> RateTableResponse` (loads latest snapshot, checks staleness, builds rate list from active CurrencyPairs); `preview_conversion(session, from_currency, to_currency, amount) -> ConversionPreviewResponse` (validates pair is active, raises `StaleRateError` if stale, calculates gross amount using snapshot rate, applies sending_fee and receiving_fee from fee config, returns full preview with snapshot_id); fee calculation must use `decimal.Decimal` throughout with ROUND_HALF_UP
- [ ] T023 [US1] Implement `GET /api/v1/fx/rates` and `POST /api/v1/fx/convert` endpoints in `src/fund_transfer/api/v1/fx.py`: inject `get_fx_provider` and `get_session` dependencies; delegate to `FxRateService`; return 503 with `STALE_EXCHANGE_RATE` error code when stale; require JWT auth on both endpoints
- [ ] T024 [US1] Register `/fx` router in `src/fund_transfer/api/v1/router.py` with prefix `/fx` and tag `FX Rates`

**Checkpoint**: `GET /api/v1/fx/rates` and `POST /api/v1/fx/convert` fully functional. All US1 tests pass. Rate table shows live rates with staleness flag. Preview returns all fee fields.

---

## Phase 4: User Story 2 — Transfer Between Own Accounts in Different Currencies (Priority: P2)

**Goal**: Authenticated customers can execute a cross-currency transfer between their own accounts — with split fees applied, PENDING→PROCESSING→COMPLETED/FAILED state machine, pessimistic account locking, rate deviation detection, and idempotency.

**Independent Test**: POST to `/api/v1/transfers/cross-currency` with own EUR→USD accounts using a fresh `snapshot_id`. Verify `status: completed`, EUR balance decreased by `source_amount + sending_fee`, USD balance increased by `net_credited_amount`. Repost with same `X-Idempotency-Key` and verify HTTP 200 with identical response and no balance change.

### Tests for User Story 2 (MANDATORY — TDD, write FIRST, verify FAIL before implementing)

- [ ] T025 [P] [US2] Write contract tests for `POST /api/v1/transfers/cross-currency`: 201 completed, 200 idempotency replay, 409 rate deviation, 422 insufficient funds, 422 unsupported pair, 503 stale rate in `tests/contract/test_cross_currency_transfers.py`
- [ ] T026 [P] [US2] Write contract test for `GET /api/v1/transfers/{id}/status`: 200 with full transfer record, 404 not found, 403 not owner in `tests/contract/test_cross_currency_transfers.py`
- [ ] T027 [P] [US2] Write integration tests for cross-currency transfer: source balance decreases by `amount + sending_fee`; destination balance increases by `net_credited_amount`; total value conserved across accounts; idempotency replay returns same transfer_id with no balance change; concurrent transfers serialised (second fails with INSUFFICIENT_FUNDS if first exhausts balance) in `tests/integration/test_cross_currency_transfers.py`
- [ ] T028 [P] [US2] Write unit tests for `CrossCurrencyTransferService`: state machine (valid and invalid transitions), fee calculation, rate deviation detection (below/above threshold), pessimistic lock behaviour with mocked repo, audit entry creation for each state transition in `tests/unit/test_cross_currency_transfer_service.py`

### Implementation for User Story 2

- [ ] T029 [P] [US2] Add cross-currency transfer schemas to `src/fund_transfer/schemas/fx.py`: `CrossCurrencyTransferRequest` (source_account_number, destination_account_number, source_amount, source_currency, destination_currency, fx_snapshot_id), `CrossCurrencyTransferResponse` (all fields from OpenAPI contract: id, status, source_amount, source_currency, sending_fee, gross_converted_amount, receiving_fee, net_credited_amount, destination_currency, exchange_rate, failure_reason, fx_snapshot_id, created_at)
- [ ] T030 [US2] Extend `TransferRepository` in `src/fund_transfer/repositories/transfer_repository.py`: add `create_cross_currency_transfer(session, ...) -> Transfer`; add `update_transfer_status(session, transfer_id, new_status, failure_reason=None) -> Transfer`; enforce valid state transitions (`PENDING→PROCESSING→COMPLETED/FAILED`) and raise `ValidationError` on invalid transition; use `SELECT FOR UPDATE` (without NOWAIT) on the source account row for pessimistic lock; write one `AuditLogEntry` per status transition inside the same `session.begin()` block with fee breakdown in `detail` JSONB
- [ ] T031 [US2] Implement `CrossCurrencyTransferService` in `src/fund_transfer/services/cross_currency_transfer_service.py`: `initiate(session, request, caller_id) -> Transfer`; check idempotency key first (return stored result if exists); check stale rates (`StaleRateError` if stale); validate currency pair is active; validate caller owns source account; acquire pessimistic lock on source account; check balance >= source_amount + sending_fee; calculate sending_fee and receiving_fee using fee config; check rate deviation between snapshot rate and current snapshot (raise `RateDeviationError` with new snapshot data if > threshold); transition `PENDING → PROCESSING → COMPLETED`; write notifications only on `COMPLETED` (own-account transfers: sender notification only); write audit entry per transition; all within single `async with session.begin()`
- [ ] T032 [US2] Implement `POST /api/v1/transfers/cross-currency` and `GET /api/v1/transfers/{id}/status` endpoints in `src/fund_transfer/api/v1/transfers.py`: require `X-Idempotency-Key` header; return 201 on new transfer, 200 on replay; return 409 with `RateDeviationError` detail on rate drift; require JWT auth and enforce owner authorization on status endpoint
- [ ] T033 [US2] Register cross-currency transfer endpoints under existing `/transfers` router in `src/fund_transfer/api/v1/router.py`

**Checkpoint**: Cross-currency transfer between own accounts fully functional. All US2 tests pass. Balance conservation verified. Idempotency confirmed. Rate deviation check returns 409 with updated snapshot.

---

## Phase 5: User Story 3 — Transfer to Another Customer's Account + Notifications (Priority: P3)

**Goal**: Customers can send cross-currency transfers to other account holders (third-party). Both sender and recipient receive an in-app notification atomically on transfer completion.

**Independent Test**: POST to `/api/v1/transfers/cross-currency` with two accounts owned by different users. Verify completion. Then `GET /api/v1/notifications?account_number=<RECIPIENT>` (authenticated as recipient) returns a `transfer_received` notification with correct amounts. Mark it read via `PATCH /api/v1/notifications/{id}/read` and verify `read_at` is set.

### Tests for User Story 3 (MANDATORY — TDD, write FIRST, verify FAIL before implementing)

- [ ] T034 [P] [US3] Write contract tests for `GET /api/v1/notifications` (200 list with unread_only filter, 403 non-owner) and `PATCH /api/v1/notifications/{id}/read` (200 with read_at set, 404 not found, 403 non-owner) in `tests/contract/test_notifications.py`
- [ ] T035 [P] [US3] Write integration test for third-party cross-currency transfer: two notifications created atomically on completion (transfer_sent for sender, transfer_received for recipient); notification metadata includes direction, source_amount, net_credited_amount, transfer_detail_url; if notification write fails, entire transaction rolls back in `tests/integration/test_cross_currency_transfers.py`
- [ ] T036 [P] [US3] Write unit tests for `NotificationService`: create sender/recipient notifications, list with unread_only filter, mark-read with owner enforcement, notification metadata shape (FR-014 fields) in `tests/unit/test_notification_service.py`

### Implementation for User Story 3

- [ ] T037 [P] [US3] Create notification schemas in `src/fund_transfer/schemas/notification.py`: `NotificationResponse` (id, recipient_account_number, transfer_id, direction, source_amount, source_currency, net_credited_amount, net_credited_currency, read_at nullable, created_at)
- [ ] T038 [US3] Implement `NotificationService` in `src/fund_transfer/services/notification_service.py`: `create_transfer_notifications(session, transfer, sender_user_id, recipient_user_id) -> None` — creates two `Notification` rows inside the caller's `session.begin()` block using `session.add() + session.flush()` (same pattern as `write_audit_log`); `list_for_user(session, user_id, unread_only) -> list[NotificationResponse]`; `mark_read(session, notification_id, user_id) -> NotificationResponse` — enforces `notification.user_id == user_id`, sets `is_read=True`, writes `notification_delivered` audit entry
- [ ] T039 [US3] Extend `CrossCurrencyTransferService` in `src/fund_transfer/services/cross_currency_transfer_service.py`: on `COMPLETED` transition for third-party transfers (source owner ≠ destination owner), call `NotificationService.create_transfer_notifications(session, transfer, sender_user_id, recipient_user_id)` inside the same transaction; own-account transfers (same owner) create sender notification only
- [ ] T040 [US3] Implement `GET /api/v1/notifications` and `PATCH /api/v1/notifications/{id}/read` endpoints in `src/fund_transfer/api/v1/notifications.py`: require JWT auth; enforce `user_id == JWT sub` on all operations; `GET` accepts `account_number` query param and `unread_only` bool; return `X-Unread-Count` header with count of unread notifications
- [ ] T041 [US3] Register `/notifications` router in `src/fund_transfer/api/v1/router.py` with prefix `/notifications` and tag `Notifications`

**Checkpoint**: All three user stories fully functional. Third-party transfers create notifications atomically. Notifications list/read endpoints work with owner enforcement.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Observability, documentation, and final validation across all user stories.

- [ ] T042 [P] Add Prometheus metrics to FX operations: `fx_rate_age_seconds` Gauge (seconds since last successful snapshot), `fx_rate_refresh_total` Counter with labels `{result: success|failure}`, `cross_currency_transfer_status_total` Counter with labels `{status: completed|failed}` — add to `src/fund_transfer/api/v1/fx.py` and `cross_currency_transfer_service.py`
- [ ] T043 [P] Add OpenTelemetry spans to `src/fund_transfer/services/fx_rate_provider.py`: span on `TreasuryFeedAdapter.refresh()` with attributes `provider_url`, `duration_ms`, `is_stale`; add span to transfer state transitions in `cross_currency_transfer_service.py` with attributes `transfer_id`, `from_status`, `to_status`
- [ ] T044 [P] Add structured log events via structlog for all new state-changing operations in `fx_rate_service.py`, `cross_currency_transfer_service.py`, `notification_service.py`: include `correlation_id` (from `X-Request-ID` middleware), `transfer_id` or `snapshot_id`, and outcome; mask account balances beyond last 4 digits in log output
- [ ] T045 [P] Update `docker-compose.yml` and `.env.example` with new environment variables: `FX_PROVIDER_URL`, `FX_RATE_MAX_AGE_MINUTES`, `FX_RATE_DEVIATION_THRESHOLD_PCT`, `FX_REFRESH_INTERVAL_SECONDS`, `USE_STATIC_RATES`
- [ ] T046 Seed `currency_pairs` table with initial supported pairs (EUR/USD, USD/EUR, EUR/GBP, GBP/EUR, etc.) matching `config/exchange_rates.yaml` — add to a data migration or startup seeding in `src/fund_transfer/main.py` lifespan
- [ ] T047 Run all quickstart.md validation scenarios end-to-end against running service: Scenarios 1–8; document any failures and fix before closing
- [ ] T048 Run full test suite with coverage report; verify unit coverage >95% for FX math and fee calculations; overall >80%; fix any gaps: `pytest --cov=src/fund_transfer --cov-report=term-missing`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories; T004 (migration) must run before T005–T010 (models); T011 (Protocol) before T012–T013 (implementations); T014 (lifespan wiring) after T012 and T013
- **Phase 3 (US1)**: Depends on Phase 2 complete — T019 (service) depends on T021 (schemas); T023 (endpoints) depends on T022 (service); T024 (router) depends on T023
- **Phase 4 (US2)**: Depends on Phase 2 complete and Phase 3 complete (reuses FxRateService for rate validation) — T031 (service) depends on T030 (schemas) and T029 (repo); T032 (endpoints) depends on T031
- **Phase 5 (US3)**: Depends on Phase 4 complete — T039 (extend service) depends on T038 (NotificationService) and T031 (CrossCurrencyTransferService); T040 (endpoints) depends on T039
- **Phase 6 (Polish)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 2 (Foundational) — no dependency on US2/US3
- **US2 (P2)**: Depends on Phase 2 and US1 (reuses FxRateService for stale check and rate lookup)
- **US3 (P3)**: Depends on Phase 2 and US2 (extends CrossCurrencyTransferService)

### Within Each Phase

1. Tests MUST be written and verified to FAIL before implementation begins
2. Models before repositories before services before endpoints
3. Within a phase, all tasks marked [P] can run concurrently
4. Commit after each logical group (model batch, service, endpoint)

### Parallel Opportunities

- T002, T003 parallel with each other (Phase 1)
- T005–T009 all parallel (Phase 2 models — different files)
- T012, T013 parallel (Phase 2 — two provider implementations)
- T015, T016 parallel (Phase 2 — two repositories)
- T017–T020 all parallel (US1 tests — different test files)
- T021 parallel with tests (US1 — schema file, no impl dependency)
- T025–T028 all parallel (US2 tests)
- T029 parallel with tests (US2 — schema file)
- T034–T036 all parallel (US3 tests)
- T037 parallel with tests (US3 — schema file)
- T042–T045 all parallel (Phase 6 — different concerns)

---

## Parallel Example: User Story 1

```
# Launch all US1 tests together (write and verify FAIL):
T017: tests/contract/test_fx_rates.py (GET /fx/rates)
T018: tests/contract/test_fx_rates.py (POST /fx/convert)
T019: tests/unit/test_fx_rate_service.py
T020: tests/unit/test_fx_rate_provider.py

# Then launch US1 implementation tasks:
T021: src/fund_transfer/schemas/fx.py (schemas — no service dependency)
T022: src/fund_transfer/services/fx_rate_service.py (after T021)
T023: src/fund_transfer/api/v1/fx.py (after T022)
T024: src/fund_transfer/api/v1/router.py (after T023)
```

## Parallel Example: User Story 2

```
# Launch all US2 tests together (write and verify FAIL):
T025: tests/contract/test_cross_currency_transfers.py (POST)
T026: tests/contract/test_cross_currency_transfers.py (GET status)
T027: tests/integration/test_cross_currency_transfers.py
T028: tests/unit/test_cross_currency_transfer_service.py

# Then launch US2 implementation:
T029: src/fund_transfer/schemas/fx.py (additive — parallel safe)
T030: src/fund_transfer/repositories/transfer_repository.py (extend)
T031: src/fund_transfer/services/cross_currency_transfer_service.py (after T029, T030)
T032: src/fund_transfer/api/v1/transfers.py (after T031)
T033: src/fund_transfer/api/v1/router.py (after T032)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T016) — CRITICAL, blocks everything
3. Complete Phase 3: User Story 1 (T017–T024)
4. **STOP and VALIDATE**: Run Scenarios 1–2 from quickstart.md
5. Deploy/demo: live rate table + conversion preview

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add US1 (rate table + preview) → Test independently → Deploy (MVP!)
3. Add US2 (own-account cross-currency transfer) → Test independently → Deploy
4. Add US3 (third-party + notifications) → Test independently → Deploy
5. Polish (observability, validation) → Production ready

### Parallel Team Strategy

With multiple developers (after Phase 2 completes):
- **Developer A**: US1 — rate table and preview endpoints
- **Developer B**: US2 — cross-currency transfer engine
- **Developer C**: US3 — notifications (depends on US2 completing first)

---

## Notes

- `[P]` tasks touch different files — safe to run concurrently
- `[Story]` label maps each task to its user story for traceability
- Each user story phase is independently deployable and testable
- Write and verify test FAILURE before any implementation line is written (Constitution §IV)
- Commit after each checkpoint (end of each phase) at minimum
- The existing `ExchangeRateService` and `exchange_rate_service.py` are untouched — backward compatibility preserved
- `SELECT FOR UPDATE` (without NOWAIT) is used for pessimistic locking — the second transfer waits rather than failing immediately; DB `statement_timeout` guards against deadlock
