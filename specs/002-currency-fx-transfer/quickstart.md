# Quickstart: Validate Currency Conversion & Cross-Currency Transfer

**Feature**: 002-currency-fx-transfer | **Date**: 2026-06-15

This guide describes how to run and validate the key scenarios from the feature spec
end-to-end once the feature is implemented. It is a validation/run guide — not an
implementation guide.

See:
- [contracts/openapi.yaml](./contracts/openapi.yaml) — full API contract
- [data-model.md](./data-model.md) — entity schema and relationships

---

## Prerequisites

1. **Docker and docker-compose** installed
2. A valid JWT Bearer token for a test user (`sub` = `test-user-001`)
3. The service running with:
   - `FX_PROVIDER_URL` set (or `USE_STATIC_RATES=true` for local dev without a live treasury feed)
   - `FX_RATE_MAX_AGE_MINUTES=60`
   - `FX_RATE_DEVIATION_THRESHOLD_PCT=1`

### Start the service

```bash
docker-compose up -d
# Wait for the service to start (health check)
curl http://localhost:8000/health
```

### Run database migrations

```bash
docker-compose exec app alembic upgrade head
```

### Seed test accounts

Create two test accounts in different currencies (EUR and USD):

```bash
# EUR account
curl -s -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"currency": "EUR", "initial_balance": "500.0000"}' | jq .

# USD account
curl -s -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"currency": "USD", "initial_balance": "0.0000"}' | jq .
```

Save the returned `account_number` values as `EUR_ACCOUNT` and `USD_ACCOUNT`.

---

## Scenario 1 — View Exchange Rate Table (FR-001, FR-003, SC-001)

**Purpose**: Verify rates are displayed with buy/sell rates and a fresh timestamp.

```bash
curl -s http://localhost:8000/api/v1/fx/rates \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Expected response**:
```json
{
  "snapshot_id": "<uuid>",
  "effective_at": "<ISO 8601 timestamp within last 60 minutes>",
  "is_stale": false,
  "rates": [
    { "from_currency": "EUR", "to_currency": "USD", "buy_rate": "1.0750", "sell_rate": "1.0720" }
  ]
}
```

**Pass criteria**:
- `is_stale` is `false`
- `effective_at` is within the last 60 minutes
- At least one rate pair is returned
- Response time < 500 ms (check with `time curl ...`)

---

## Scenario 2 — Preview Currency Conversion (FR-002, FR-005)

**Purpose**: Verify conversion preview shows split fees and net amount.

```bash
curl -s -X POST http://localhost:8000/api/v1/fx/convert \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_currency": "EUR",
    "to_currency": "USD",
    "amount": "100.0000"
  }' | jq .
```

**Expected response**:
```json
{
  "from_currency": "EUR",
  "to_currency": "USD",
  "input_amount": "100.0000",
  "exchange_rate": "1.07500000",
  "gross_converted_amount": "107.5000",
  "estimated_sending_fee": "2.0000",
  "estimated_receiving_fee": "1.0750",
  "estimated_net_amount": "106.4250",
  "total_sender_cost": "102.0000",
  "snapshot_id": "<uuid>",
  "effective_at": "<timestamp>",
  "is_stale": false
}
```

**Pass criteria**:
- All fee fields are present and non-negative
- `estimated_net_amount` = `gross_converted_amount - estimated_receiving_fee`
- `total_sender_cost` = `input_amount + estimated_sending_fee`
- `snapshot_id` matches the most recent rate snapshot

Save the returned `snapshot_id` as `SNAPSHOT_ID`.

---

## Scenario 3 — Execute Cross-Currency Transfer (FR-004, FR-007, SC-002, SC-003)

**Purpose**: Verify atomic debit/credit with split fees.

```bash
curl -s -X POST http://localhost:8000/api/v1/transfers/cross-currency \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: test-xfer-001" \
  -d "{
    \"source_account_number\": \"$EUR_ACCOUNT\",
    \"destination_account_number\": \"$USD_ACCOUNT\",
    \"source_amount\": \"100.0000\",
    \"source_currency\": \"EUR\",
    \"destination_currency\": \"USD\",
    \"fx_snapshot_id\": \"$SNAPSHOT_ID\"
  }" | jq .
```

**Expected response** (HTTP 201):
```json
{
  "id": "<transfer-uuid>",
  "status": "completed",
  "source_account_number": "<EUR_ACCOUNT>",
  "destination_account_number": "<USD_ACCOUNT>",
  "source_amount": "100.0000",
  "source_currency": "EUR",
  "sending_fee": "2.0000",
  "gross_converted_amount": "107.5000",
  "receiving_fee": "1.0750",
  "net_credited_amount": "106.4250",
  "destination_currency": "USD",
  "exchange_rate": "1.07500000",
  "failure_reason": null,
  "fx_snapshot_id": "<SNAPSHOT_ID>"
}
```

**Pass criteria**:
- `status` = `completed`
- EUR account balance decreased by `source_amount + sending_fee` = 102.00
- USD account balance increased by `net_credited_amount` = 106.4250
- Verify balances via `GET /api/v1/accounts/{account_number}`

---

## Scenario 4 — Idempotency Replay (FR-010, SC-006)

**Purpose**: Resubmitting the same transfer returns the original result, no double-debit.

```bash
# Resubmit the exact same request with the same X-Idempotency-Key
curl -s -X POST http://localhost:8000/api/v1/transfers/cross-currency \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: test-xfer-001" \
  -d "{
    \"source_account_number\": \"$EUR_ACCOUNT\",
    \"destination_account_number\": \"$USD_ACCOUNT\",
    \"source_amount\": \"100.0000\",
    \"source_currency\": \"EUR\",
    \"destination_currency\": \"USD\",
    \"fx_snapshot_id\": \"$SNAPSHOT_ID\"
  }" | jq .
```

**Expected response** (HTTP 200 — replay):
- Same transfer `id` as the original response
- Balances unchanged from the end of Scenario 3

---

## Scenario 5 — Insufficient Funds Rejection (FR-008)

**Purpose**: Verify transfer is rejected cleanly when source balance is insufficient.

```bash
curl -s -X POST http://localhost:8000/api/v1/transfers/cross-currency \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: test-xfer-002" \
  -d "{
    \"source_account_number\": \"$EUR_ACCOUNT\",
    \"destination_account_number\": \"$USD_ACCOUNT\",
    \"source_amount\": \"99999.0000\",
    \"source_currency\": \"EUR\",
    \"destination_currency\": \"USD\",
    \"fx_snapshot_id\": \"$SNAPSHOT_ID\"
  }" | jq .
```

**Expected response** (HTTP 422):
```json
{
  "error_code": "INSUFFICIENT_FUNDS",
  "message": "Insufficient balance. Required: 100001.0000 EUR, Available: <balance> EUR."
}
```

**Pass criteria**:
- HTTP 422 returned
- EUR account balance unchanged
- No audit log entry for a completed transfer

---

## Scenario 6 — Stale Rate Blocks Transfer (FR-003a, Edge Case)

**Purpose**: Verify that stale rates block transfer initiation but allow rate viewing.

Simulate stale rates by temporarily setting `FX_RATE_MAX_AGE_MINUTES=0` or by waiting
for the snapshot to age, then:

```bash
# Rate table still accessible (is_stale: true)
curl -s http://localhost:8000/api/v1/fx/rates \
  -H "Authorization: Bearer $TOKEN" | jq '.is_stale'
# Expected: true

# Transfer initiation blocked
curl -s -X POST http://localhost:8000/api/v1/transfers/cross-currency \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: test-xfer-003" \
  -d '{ ... }' | jq '.error_code'
# Expected: "STALE_EXCHANGE_RATE" (HTTP 503)
```

---

## Scenario 7 — In-App Notifications (FR-013, FR-014)

**Purpose**: Verify notifications are created for both sender and recipient on P3 transfer completion.

After completing Scenario 3:

```bash
# Check sender notifications
curl -s "http://localhost:8000/api/v1/notifications?account_number=$EUR_ACCOUNT" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Check recipient notifications (requires recipient auth token)
curl -s "http://localhost:8000/api/v1/notifications?account_number=$USD_ACCOUNT" \
  -H "Authorization: Bearer $RECIPIENT_TOKEN" | jq .

# Mark a notification as read
NOTIF_ID=$(curl -s "http://localhost:8000/api/v1/notifications?account_number=$EUR_ACCOUNT" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')

curl -s -X PATCH "http://localhost:8000/api/v1/notifications/$NOTIF_ID/read" \
  -H "Authorization: Bearer $TOKEN" | jq '.read_at'
# Expected: ISO 8601 timestamp (not null)
```

**Pass criteria**:
- Exactly 2 notifications created per completed cross-currency transfer (one sent, one received)
- `metadata` contains direction, source amount, net credited amount, transfer detail URL
- `read_at` is set after marking read

---

## Scenario 8 — Audit Trail Completeness (SC-004)

**Purpose**: Verify 100% audit coverage for transfer lifecycle.

After Scenarios 3 and 5, query the audit log directly (requires DB access or admin endpoint):

```sql
SELECT operation_type, actor_identity, outcome, detail
FROM audit_log
ORDER BY timestamp DESC
LIMIT 10;
```

**Expected entries** (at minimum):
- `cross_currency_transfer_initiated` — for Scenario 3 (PENDING)
- `cross_currency_transfer_completed` — for Scenario 3 (COMPLETED)
- `cross_currency_transfer_failed` — for Scenario 5 (insufficient funds)
- `notification_delivered` × 2 — for Scenario 7

**Pass criteria**:
- Every state transition has exactly one corresponding audit entry
- `detail` JSONB includes fee breakdown (sending_fee, receiving_fee, net_credited)
- `initiator` matches the JWT `sub` of the authenticated caller

---

## Running the Automated Test Suite

Unit tests (no database required):

```bash
pytest tests/unit/test_fx_rate_service.py \
       tests/unit/test_fx_rate_provider.py \
       tests/unit/test_notification_service.py \
       -v
```

Integration tests (requires running PostgreSQL):

```bash
pytest tests/integration/test_cross_currency_transfers.py -v
```

Contract tests (requires running service):

```bash
pytest tests/contract/test_fx_rates.py \
       tests/contract/test_notifications.py \
       -v
```

Full suite with coverage:

```bash
pytest --cov=src/fund_transfer --cov-report=term-missing
# Target: unit >95% for FX math; overall >80%
```
