# Quickstart: Recurring Scheduled Transfer Validation Guide

**Phase**: 1 — Design | **Date**: 2026-06-16
**References**: [spec.md](./spec.md) | [data-model.md](./data-model.md) | [contracts/openapi.yaml](./contracts/openapi.yaml)

This guide documents runnable validation scenarios that prove the Recurring Scheduled
Transfer feature works end-to-end. Run these after the service is standing.

---

## Prerequisites

- Docker and docker-compose installed (same as Fund Transfer Service, spec 001)
- `curl` or an HTTP client (Postman, httpx)
- A valid JWT Bearer token for a test user
- At least one account and one beneficiary registered (from spec 001 setup)

---

## Environment Setup

```bash
# 1. Start the service (scheduler starts automatically in FastAPI lifespan)
docker-compose up -d

# 2. Wait for healthy
curl -f http://localhost:8000/health   # {"status": "ok"}

# 3. Set auth token
export TOKEN="Bearer <your-test-jwt>"
export BASE="http://localhost:8000/v1"

# 4. Capture IDs from spec 001 setup
export ACCOUNT_ID="<your-source-account-uuid>"
export BENEFICIARY_ID="<your-beneficiary-uuid>"
```

---

## Scenario 1: Create a Monthly Schedule

**Validates**: FR-001, FR-002, FR-003, SC-001

```bash
curl -s -X POST "$BASE/schedules" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Monthly Rent",
    "source_account_id": "'$ACCOUNT_ID'",
    "beneficiary_id": "'$BENEFICIARY_ID'",
    "amount": "1250.00",
    "currency": "EUR",
    "interval": "monthly",
    "start_date": "'$(date -d '+1 month' +%Y-%m-01)'",
    "end_date": "'$(date -d '+13 months' +%Y-%m-01)'"
  }' | python3 -m json.tool
```

**Expected**:
- HTTP 201
- `schedule.status` = `"ACTIVE"`
- `all_execution_dates` contains exactly 12 dates (monthly over 12 months)
- `schedule.delegated_jwt_expires_at` is approximately 30 days from now
- `schedule.beneficiary_account_masked` shows `"****XXXX"` (last 4 digits only)

```bash
# Capture schedule ID for subsequent tests
export SCHEDULE_ID=$(curl -s ... | python3 -c "import sys,json; print(json.load(sys.stdin)['schedule']['id'])")
```

---

## Scenario 2: Validation Rejects Invalid Inputs

**Validates**: FR-002

```bash
# Start date in the past → expect 422
curl -s -X POST "$BASE/schedules" \
  -H "Authorization: $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Bad","source_account_id":"'$ACCOUNT_ID'","beneficiary_id":"'$BENEFICIARY_ID'",
       "amount":"100.00","currency":"EUR","interval":"monthly",
       "start_date":"2020-01-01","end_date":"2020-12-01"}' \
  -o /dev/null -w "%{http_code}"
# Expected: 422

# End date before start date → expect 422
curl -s -X POST "$BASE/schedules" \
  -H "Authorization: $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Bad","source_account_id":"'$ACCOUNT_ID'","beneficiary_id":"'$BENEFICIARY_ID'",
       "amount":"100.00","currency":"EUR","interval":"monthly",
       "start_date":"2027-06-01","end_date":"2027-01-01"}' \
  -o /dev/null -w "%{http_code}"
# Expected: 422
```

---

## Scenario 3: List and View Schedules

**Validates**: FR-013, FR-002, SEC-002 (masked account)

```bash
# List all schedules
curl -s "$BASE/schedules" -H "Authorization: $TOKEN" | python3 -m json.tool
# Expected: items array contains the schedule; beneficiary_account_masked shows ****XXXX

# Get schedule detail
curl -s "$BASE/schedules/$SCHEDULE_ID" -H "Authorization: $TOKEN" | python3 -m json.tool
# Expected: upcoming_execution_dates shows next 5 dates
```

---

## Scenario 4: Pause and Resume

**Validates**: FR-005, FR-006, state machine

```bash
# Pause
curl -s -X POST "$BASE/schedules/$SCHEDULE_ID/pause" \
  -H "Authorization: $TOKEN" | python3 -m json.tool
# Expected: status = "PAUSED"

# Verify list shows PAUSED
curl -s "$BASE/schedules?status=PAUSED" -H "Authorization: $TOKEN" | python3 -m json.tool

# Resume
curl -s -X POST "$BASE/schedules/$SCHEDULE_ID/resume" \
  -H "Authorization: $TOKEN" | python3 -m json.tool
# Expected: status = "ACTIVE"
```

---

## Scenario 5: Modify Amount

**Validates**: FR-006, version increment

```bash
curl -s -X PATCH "$BASE/schedules/$SCHEDULE_ID" \
  -H "Authorization: $TOKEN" -H "Content-Type: application/json" \
  -d '{"amount": "1350.00"}' | python3 -m json.tool
# Expected: amount = "1350.00000000"; version incremented by 1
```

---

## Scenario 6: Trigger Execution (Integration Test)

**Validates**: FR-007, FR-010, SEC-003, DI-002 (idempotency), SC-002, SC-003

This test bypasses the time-based scheduler to trigger execution immediately.
Use the internal test endpoint (available only in `TESTING=true` mode):

```bash
# Force-trigger the next execution for a schedule (test mode only)
curl -s -X POST "$BASE/schedules/$SCHEDULE_ID/test-execute" \
  -H "Authorization: $TOKEN" | python3 -m json.tool
# Expected:
#   status = "SUCCEEDED"
#   transfer_id is a valid UUID
#   schedule.last_executed_at updated
#   schedule.execution_count = 1

# Trigger again immediately — idempotency check
curl -s -X POST "$BASE/schedules/$SCHEDULE_ID/test-execute" \
  -H "Authorization: $TOKEN" | python3 -m json.tool
# Expected: status = "already_executed" — no second transfer created
```

---

## Scenario 7: Execution History

**Validates**: FR-010

```bash
curl -s "$BASE/schedules/$SCHEDULE_ID/executions" \
  -H "Authorization: $TOKEN" | python3 -m json.tool
# Expected:
#   items[0].status = "SUCCEEDED"
#   items[0].transfer_id is populated
#   items[0].occurrence_date and execution_date are present
```

---

## Scenario 8: Cancel and Verify No Further Execution

**Validates**: FR-011, FR-005, state machine (terminal state)

```bash
# Cancel
curl -s -X POST "$BASE/schedules/$SCHEDULE_ID/cancel" \
  -H "Authorization: $TOKEN" | python3 -m json.tool
# Expected: status = "CANCELLED"

# Attempt invalid transition (pause a CANCELLED schedule) → expect 409
curl -s -X POST "$BASE/schedules/$SCHEDULE_ID/pause" \
  -H "Authorization: $TOKEN" -o /dev/null -w "%{http_code}"
# Expected: 409
```

---

## Scenario 9: Per-User Limit Enforcement

**Validates**: FR-014

```bash
# Create 20 schedules (use a script loop)
for i in $(seq 1 20); do
  curl -s -X POST "$BASE/schedules" -H "Authorization: $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"Schedule '$i'","source_account_id":"'$ACCOUNT_ID'",
         "beneficiary_id":"'$BENEFICIARY_ID'","amount":"10.00","currency":"EUR",
         "interval":"annually","start_date":"2027-01-01","end_date":"2027-12-31"}' \
    -o /dev/null -w "%{http_code}\n"
done
# Expected: first 20 return 201; 21st returns 422 with limit-reached message
```

---

## Scenario 10: Cross-User Isolation (Security)

**Validates**: SEC-001, SEC-002, SC-004

```bash
# Using a second user's token, attempt to access the first user's schedule
export TOKEN_USER2="Bearer <second-user-jwt>"
curl -s "$BASE/schedules/$SCHEDULE_ID" \
  -H "Authorization: $TOKEN_USER2" -o /dev/null -w "%{http_code}"
# Expected: 404 (not 403 — schedule must not even be acknowledged to exist)
```

---

## Audit Log Verification

**Validates**: SEC-004, DI-004, SC-006

```bash
# Query audit log for all schedule operations (requires DB access or admin endpoint)
psql $DATABASE_URL -c "
  SELECT operation_type, initiator, timestamp
  FROM audit_log
  WHERE operation_type LIKE 'SCHEDULE_%'
  ORDER BY timestamp DESC
  LIMIT 20;
"
# Expected:
#   SCHEDULE_CREATED entry with initiator = authenticated user sub
#   SCHEDULE_EXECUTION_SUCCEEDED entry with initiator = 'system/scheduler (on behalf of user/...)'
#   SCHEDULE_CANCELLED entry with initiator = authenticated user sub
```

---

## Cleanup

```bash
docker-compose down -v   # removes containers and test DB volume
```
