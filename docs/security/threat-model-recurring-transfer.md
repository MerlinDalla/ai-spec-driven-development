# STRIDE Threat Model: Recurring Scheduled Transfer

**Date**: 2026-06-16
**Feature**: Recurring Scheduled Transfer (spec 007)
**Framework**: STRIDE + CIA triad; CAPEC references for highest-risk paths
**Evidence directory**: `docs/security/`

---

## Trust Boundaries

| ID | Boundary | Crosses |
|----|----------|---------|
| TB-1 | User ↔ Scheduling API | HTTP/JWT; user creates, views, modifies schedules |
| TB-2 | Scheduling API ↔ Scheduler Engine | In-process; delegated JWT boundary |
| TB-3 | Scheduler Engine ↔ Fund Transfer Execution | Internal service call; system-scoped delegated JWT |

---

## Threat Analysis

### TB-1: User ↔ Scheduling API

#### T-001 — Spoofing: Attacker impersonates a user to create or cancel their schedules
- **STRIDE**: Spoofing
- **CIA**: Confidentiality (access to schedule data), Integrity (rogue schedule creation)
- **CAPEC**: CAPEC-194 (Fake the Source of Data)
- **Likelihood**: Medium (token theft is common)
- **Impact**: High (attacker can move victim's money on a recurring basis)
- **Mitigation**: JWT signature validation on every request; short token TTL (15 min access token); refresh token rotation. Schedule creation records the authenticated `sub` claim, not a user-supplied user ID.
- **Status**: Mitigated ✅

#### T-002 — Tampering: Attacker modifies schedule request in transit (MITM)
- **STRIDE**: Tampering
- **CIA**: Integrity (amount or beneficiary changed mid-flight)
- **CAPEC**: CAPEC-94 (Man in the Middle Attack)
- **Likelihood**: Low (TLS enforced)
- **Impact**: High (wrong amount or beneficiary)
- **Mitigation**: TLS 1.2+ enforced for all API communication; HSTS enabled; certificate pinning recommended for mobile clients.
- **Status**: Mitigated ✅

#### T-003 — Repudiation: User denies creating or authorising a schedule
- **STRIDE**: Repudiation
- **CIA**: Integrity (auditability)
- **Likelihood**: Medium (dispute resolution is common in banking)
- **Impact**: Medium (regulatory and legal exposure)
- **Mitigation**: `SCHEDULE_CREATED` audit log entry records `sub` claim, timestamp (server-set), request IP, and user agent. Audit log is append-only and immutable. Delegated JWT stored as evidence of user authorisation scope.
- **Status**: Mitigated ✅

#### T-004 — Information Disclosure: Attacker reads another user's schedule data
- **STRIDE**: Information Disclosure
- **CIA**: Confidentiality
- **CAPEC**: CAPEC-122 (Privilege Abuse)
- **Likelihood**: Medium (IDOR is common if IDs are sequential or guessable)
- **Impact**: High (beneficiary and amount patterns reveal spending behaviour)
- **Mitigation**: Schedule IDs are UUIDs (not guessable). API query is always scoped to `user_id` from JWT `sub`; user-supplied user IDs are never trusted. Schedule detail returns 404 (not 403) for cross-user access attempts to avoid confirming existence.
- **Status**: Mitigated ✅

#### T-005 — Denial of Service: Attacker floods schedule creation endpoint
- **STRIDE**: Denial of Service
- **CIA**: Availability
- **CAPEC**: CAPEC-469 (HTTP DoS)
- **Likelihood**: Medium
- **Impact**: Medium (service degradation for all users)
- **Mitigation**: Per-user rate limiting on schedule creation (max 10 creates/minute); per-user active schedule limit (20 schedules); API gateway rate limiting inherited from spec 001.
- **Status**: Mitigated ✅

#### T-006 — Elevation of Privilege: Attacker accesses admin/internal schedule endpoints
- **STRIDE**: Elevation of Privilege
- **CIA**: Integrity, Availability
- **CAPEC**: CAPEC-122 (Privilege Abuse)
- **Likelihood**: Low
- **Impact**: Critical (could modify or delete any user's schedule)
- **Mitigation**: Internal test-execution endpoint (`/test-execute`) is only available when `TESTING=true` environment variable is set; disabled in production. All admin operations require a separate admin role claim in JWT; not grantable by the standard user authentication flow.
- **Status**: Mitigated ✅

---

### TB-2: Scheduling API ↔ Scheduler Engine (in-process)

#### T-007 — Tampering: Delegated JWT is modified in storage before execution
- **STRIDE**: Tampering
- **CIA**: Integrity (scheduler executes with forged scope)
- **CAPEC**: CAPEC-248 (Command Injection)
- **Likelihood**: Low (requires DB write access)
- **Impact**: Critical (attacker could change target account or amount)
- **Mitigation**: Delegated JWT is AES-256 encrypted before storage. JWT signature verification at execution time detects any tampering with the payload. Even if the ciphertext is replaced, the signature check fails and the execution is aborted with an audit log entry.
- **Status**: Mitigated ✅

#### T-008 — Repudiation: Scheduler claims not to have executed a transfer
- **STRIDE**: Repudiation
- **CIA**: Integrity
- **Likelihood**: Low (system actor, not human)
- **Impact**: Medium (execution disputes, double-payment investigations)
- **Mitigation**: `SCHEDULE_EXECUTION_SUCCEEDED` audit log entry is written in the same ACID transaction as the transfer; contains `schedule_id`, `occurrence_date`, `transfer_id`, `initiator` = `system/scheduler (on behalf of user/{sub})`, and server-set timestamp. The `ScheduleExecution` record is immutable.
- **Status**: Mitigated ✅

#### T-009 — Denial of Service: Scheduler job table poisoned with invalid job records
- **STRIDE**: Denial of Service
- **CIA**: Availability
- **Likelihood**: Very Low (requires DB access)
- **Impact**: Medium (scheduler fails to fire legitimate jobs)
- **Mitigation**: APScheduler job table is append-only from the scheduler's perspective; only the scheduler process writes to it. DB user used by the application has no DELETE or DROP permission on this table. Scheduler monitors for job table corruption via alerting on `execution_lag_seconds`.
- **Status**: Mitigated ✅

---

### TB-3: Scheduler Engine ↔ Fund Transfer Execution

#### T-010 — Spoofing: Attacker injects forged execution requests into the transfer service
- **STRIDE**: Spoofing
- **CIA**: Integrity (unauthorised fund movement)
- **CAPEC**: CAPEC-194 (Fake the Source of Data)
- **Likelihood**: Low (internal boundary, but worth modelling)
- **Impact**: Critical
- **Mitigation**: Delegated JWT presented to the fund transfer service; the service validates signature, issuer (`fund-transfer-service/scheduler`), audience (`internal/transfer-execution`), expiry, and scope constraints before processing. Requests without a valid delegated JWT are rejected.
- **Status**: Mitigated ✅

#### T-011 — Tampering: Execution request modified between scheduler and transfer service
- **STRIDE**: Tampering
- **CIA**: Integrity
- **Likelihood**: Very Low (in-process call; no network crossing)
- **Impact**: High
- **Mitigation**: In-process function call (no serialisation/deserialisation over a network). If extracted to a microservice in future, TLS + request signing must be added. This is a re-evaluation trigger for S-ADR-001.
- **Status**: Mitigated for current architecture ✅ | ⚠ Re-evaluate if microservice extraction occurs

#### T-012 — Elevation of Privilege: Scheduler executes transfers beyond the delegated scope
- **STRIDE**: Elevation of Privilege
- **CIA**: Integrity (excess fund movement)
- **CAPEC**: CAPEC-122 (Privilege Abuse)
- **Likelihood**: Low (requires bug in scope enforcement)
- **Impact**: Critical
- **Mitigation**: Fund transfer service enforces scope constraints from the delegated JWT (`source_account_id`, `beneficiary_id`, `max_amount`) as a separate validation step, independent of the scheduler. Scope violations are logged and rejected even if the JWT signature is valid. Unit tests cover all scope boundary conditions (>95% coverage required).
- **Status**: Mitigated ✅

---

## Summary Risk Register

| ID | Threat | Likelihood | Impact | Residual Risk | Status |
|----|--------|-----------|--------|---------------|--------|
| T-001 | Spoofing via token theft | Medium | High | Low | ✅ |
| T-002 | MITM tampering | Low | High | Very Low | ✅ |
| T-003 | User repudiates schedule | Medium | Medium | Low | ✅ |
| T-004 | IDOR — cross-user read | Medium | High | Low | ✅ |
| T-005 | Schedule creation DoS | Medium | Medium | Low | ✅ |
| T-006 | Admin endpoint privilege escalation | Low | Critical | Very Low | ✅ |
| T-007 | Delegated JWT storage tampering | Low | Critical | Very Low | ✅ |
| T-008 | Scheduler execution repudiation | Low | Medium | Very Low | ✅ |
| T-009 | Job table poisoning | Very Low | Medium | Very Low | ✅ |
| T-010 | Forged execution requests | Low | Critical | Very Low | ✅ |
| T-011 | In-process tampering | Very Low | High | Very Low | ⚠ Review on microservice split |
| T-012 | Scope escalation in execution | Low | Critical | Very Low | ✅ |

**Overall residual risk**: Low. All critical-impact threats have been mitigated to Very Low residual risk. T-011 requires re-evaluation if the architecture is extracted to a microservice.

---

## CAPEC References (Highest-Risk Paths)

- **CAPEC-194** (Fake the Source of Data): addressed by JWT signature validation at all boundaries.
- **CAPEC-122** (Privilege Abuse): addressed by scope-narrowed delegated JWT and dual enforcement (scheduler + transfer service).
- **CAPEC-94** (Man in the Middle): addressed by mandatory TLS at all external boundaries.
