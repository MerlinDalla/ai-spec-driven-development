# Quickstart: Fund Transfer Service Validation Guide

**Phase**: 1 — Design | **Date**: 2026-06-15
**References**: [spec.md](./spec.md) | [data-model.md](./data-model.md) | [contracts/openapi.yaml](./contracts/openapi.yaml)

This guide documents the end-to-end validation scenarios that prove the Fund Transfer
Service works correctly. Run these after standing up the service locally.

---

## Prerequisites

- Docker and docker-compose installed
- `curl` or an HTTP client (Postman, httpx)
- A valid JWT Bearer token for a test user (see Environment Setup)

## Environment Setup

```bash
# 1. Clone and enter the project
cd fund-transfer-service

# 2. Copy environment template and fill in values
cp .env.example .env
# Required variables:
#   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fund_transfer
#   JWKS_URI=http://localhost:8080/.well-known/jwks.json   (or upstream IdP)
#   EXCHANGE_RATES_CONFIG=config/exchange_rates.yaml
#   JWT_AUDIENCE=fund-transfer-service

# 3. Start the service and database
docker-compose up -d

# 4. Wait for the service to be healthy
curl -f http://localhost:8000/health  # should return {"status": "ok"}

# 5. Obtain a test JWT
# If using a mock IdP for local dev:
export TOKEN="Bearer <your-test-jwt>"
```

---

## Scenario 1 — Create a New Account (US1)

**Covers**: FR-001, FR-002, SC-001

### Happy Path: Valid account creation

```bash
curl -s -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"owner_id": "user-test-001", "currency": "EUR", "opening_balance": "1000.0000"}' | jq .
```

**Expected** (HTTP 201):
```json
{
  "account_number": "ACCT-EUR<unique>",
  "owner_id": "user-test-001",
  "currency": "EUR",
  "balance": "1000.0000",
  "status": "active"
}
```
- `account_number` is unique on every call
- `balance` equals `opening_balance` exactly

### Validation: Negative opening balance (FR-001)

```bash
curl -s -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"owner_id": "user-test-001", "currency": "EUR", "opening_balance": "-50.0000"}' | jq .
```

**Expected** (HTTP 400): `error_code: VALIDATION_ERROR` — no account created

### Validation: Unsupported currency (DI-005)

```bash
curl -s -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"owner_id": "user-test-001", "currency": "XYZ", "opening_balance": "0.0000"}' | jq .
```

**Expected** (HTTP 400): `error_code: UNSUPPORTED_CURRENCY`

---

## Scenario 2 — Retrieve Account Balance (US2)

**Covers**: FR-003, SC-002

### Setup: Create two test accounts and note their account numbers

```bash
ACCT_A=$(curl -s -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"owner_id": "user-test-001", "currency": "EUR", "opening_balance": "2000.0000"}' \
  | jq -r '.account_number')

ACCT_B=$(curl -s -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"owner_id": "user-test-002", "currency": "EUR", "opening_balance": "500.0000"}' \
  | jq -r '.account_number')

echo "Account A: $ACCT_A  |  Account B: $ACCT_B"
```

### Happy Path: Retrieve balance

```bash
curl -s http://localhost:8000/api/v1/accounts/$ACCT_A \
  -H "Authorization: $TOKEN" | jq .
```

**Expected** (HTTP 200): `balance` equals `"2000.0000"` exactly

### Not-found case (FR-003)

```bash
curl -s http://localhost:8000/api/v1/accounts/ACCT-NOTEXIST0001 \
  -H "Authorization: $TOKEN" | jq .
```

**Expected** (HTTP 404): `error_code: ACCOUNT_NOT_FOUND`

---

## Scenario 3 — Transfer Funds Between Accounts (US3)

**Covers**: FR-004, FR-005, FR-006, FR-009, FR-010, SC-003, SC-004, SC-005

> Uses `$ACCT_A` (2000 EUR) and `$ACCT_B` (500 EUR) created in Scenario 2.

### Happy Path: Valid same-currency transfer

```bash
curl -s -X POST http://localhost:8000/api/v1/transfers \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: transfer-test-001" \
  -d "{\"source_account_number\": \"$ACCT_A\", \"destination_account_number\": \"$ACCT_B\", \"amount\": \"250.0000\"}" | jq .
```

**Expected** (HTTP 201):
- `status: "completed"`
- `source_amount: "250.0000"`, `exchange_rate: "1.00000000"`

**Verify balances** (SC-003, SC-004):
```bash
curl -s http://localhost:8000/api/v1/accounts/$ACCT_A -H "Authorization: $TOKEN" | jq .balance
# Expected: "1750.0000"
curl -s http://localhost:8000/api/v1/accounts/$ACCT_B -H "Authorization: $TOKEN" | jq .balance
# Expected: "750.0000"
```

### Idempotency: Duplicate request (FR-009, SC-005)

```bash
# Same idempotency key, same body — must return original response
curl -s -X POST http://localhost:8000/api/v1/transfers \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: transfer-test-001" \
  -d "{\"source_account_number\": \"$ACCT_A\", \"destination_account_number\": \"$ACCT_B\", \"amount\": \"250.0000\"}" | jq .
```

**Expected** (HTTP 200): Same `transfer_id` as the first call; `X-Idempotency-Replay: true` header;
`$ACCT_A` balance unchanged at `"1750.0000"`.

### Insufficient funds (FR-005, SC-007)

```bash
curl -s -X POST http://localhost:8000/api/v1/transfers \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: transfer-test-002" \
  -d "{\"source_account_number\": \"$ACCT_A\", \"destination_account_number\": \"$ACCT_B\", \"amount\": \"9999.0000\"}" | jq .
```

**Expected** (HTTP 422): `error_code: INSUFFICIENT_FUNDS` — balances unchanged

### Zero/negative amount (FR-006)

```bash
curl -s -X POST http://localhost:8000/api/v1/transfers \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: transfer-test-003" \
  -d "{\"source_account_number\": \"$ACCT_A\", \"destination_account_number\": \"$ACCT_B\", \"amount\": \"0.0000\"}" | jq .
```

**Expected** (HTTP 400): `error_code: VALIDATION_ERROR`

### Transfer limit exceeded (FR-011, SC-009)

```bash
curl -s -X POST http://localhost:8000/api/v1/transfers \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: transfer-test-004" \
  -d "{\"source_account_number\": \"$ACCT_A\", \"destination_account_number\": \"$ACCT_B\", \"amount\": \"1500000.0000\"}" | jq .
```

**Expected** (HTTP 422): `error_code: TRANSFER_LIMIT_EXCEEDED`

### Non-existent account (FR-004)

```bash
curl -s -X POST http://localhost:8000/api/v1/transfers \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: transfer-test-005" \
  -d "{\"source_account_number\": \"ACCT-NOTEXIST0001\", \"destination_account_number\": \"$ACCT_B\", \"amount\": \"100.0000\"}" | jq .
```

**Expected** (HTTP 404): `error_code: ACCOUNT_NOT_FOUND`

### Multi-currency transfer (FR-012, SC-010)

```bash
ACCT_USD=$(curl -s -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"owner_id": "user-test-002", "currency": "USD", "opening_balance": "0.0000"}' \
  | jq -r '.account_number')

curl -s -X POST http://localhost:8000/api/v1/transfers \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: transfer-test-006" \
  -d "{\"source_account_number\": \"$ACCT_A\", \"destination_account_number\": \"$ACCT_USD\", \"amount\": \"100.0000\"}" | jq .
```

**Expected** (HTTP 201):
- `source_currency: "EUR"`, `destination_currency: "USD"`
- `exchange_rate` matches configured EUR→USD rate (e.g., `"1.08500000"`)
- `destination_amount = source_amount × exchange_rate` (e.g., `"108.5000"`)
- Audit log entry includes `exchange_rate` and `destination_amount`

---

## Scenario 4 — Delete an Account (US4)

**Covers**: FR-007, SC-006

### Happy Path: Delete zero-balance account

```bash
# Create a fresh account with zero balance
ACCT_DEL=$(curl -s -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"owner_id": "user-test-001", "currency": "EUR", "opening_balance": "0.0000"}' \
  | jq -r '.account_number')

curl -s -X DELETE http://localhost:8000/api/v1/accounts/$ACCT_DEL \
  -H "Authorization: $TOKEN"
# Expected: HTTP 204 No Content

# Verify: account no longer retrievable
curl -s http://localhost:8000/api/v1/accounts/$ACCT_DEL \
  -H "Authorization: $TOKEN" | jq .error_code
# Expected: "ACCOUNT_NOT_FOUND"
```

### Reject: Delete account with non-zero balance

```bash
curl -s -X DELETE http://localhost:8000/api/v1/accounts/$ACCT_A \
  -H "Authorization: $TOKEN" | jq .
```

**Expected** (HTTP 400): `error_code: ACCOUNT_HAS_BALANCE`

---

## Automated Test Suite

Once the service is running, the full automated test suite covers all scenarios above:

```bash
# Run unit tests (no DB required)
pytest tests/unit/ -v --cov=src/fund_transfer --cov-fail-under=95

# Run integration tests (requires PostgreSQL via docker-compose)
pytest tests/integration/ -v --cov=src/fund_transfer --cov-fail-under=80

# Run contract tests (validates behavior against OpenAPI spec)
pytest tests/contract/ -v

# Run full suite
pytest tests/ -v
```

**Load validation** (PERF-001, PERF-002, PERF-003):
```bash
# Start locust load test against running service
locust -f tests/load/locustfile.py --host http://localhost:8000 \
  --users 500 --spawn-rate 50 --run-time 60s --headless
# Verify: p95 read < 500ms, p95 write < 2s, 0 errors
```

---

## Health and Observability Checks

```bash
# Service health
curl http://localhost:8000/health

# Prometheus metrics (verify counters increment on each operation)
curl http://localhost:8000/metrics | grep fund_transfer

# Structured log output (check correlation IDs)
docker-compose logs fund-transfer-service | jq '.request_id, .operation, .outcome'
```