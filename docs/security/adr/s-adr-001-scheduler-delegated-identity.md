# S-ADR-001: Scheduler Delegated Identity Model

**Status**: Accepted
**Date**: 2026-06-16
**Feature**: Recurring Scheduled Transfer (spec 007)
**Author**: AI Spec Driven Platform Team
**Evidence directory**: `docs/security/adr/`

---

## Context

The Recurring Scheduled Transfer feature introduces a scheduling engine that executes
fund transfers autonomously — without a live user session present at execution time.
This creates a new trust boundary: the scheduler must act on behalf of a specific user,
but cannot rely on a user-provided JWT because no user is logged in.

The key architectural question is: **how does the scheduling engine prove to the fund
transfer service that it is authorised to move a specific user's funds?**

Without a formal answer, two dangerous defaults emerge:
1. **Ambient system trust**: the scheduler runs as a privileged `system` user with
   blanket permission to move any user's funds — catastrophic if compromised.
2. **Stored user credentials**: the user's original JWT or password is stored and
   reused at execution time — violates Zero Trust and token hygiene.

Neither is acceptable in a banking system.

---

## Decision

**Use an encrypted, scope-narrowed delegated JWT, generated at schedule creation time
(when the user is present), stored encrypted in the database, and validated at each
execution.**

### Mechanism

1. **At schedule creation** (live user session): the API generates a short-lived JWT
   with the following claims:
   - `sub`: user's UUID (the principal — who authorised this)
   - `act`: `"scheduler"` (the actor — who is executing)
   - `schedule_id`: UUID of this specific schedule
   - `scope.source_account_id`: locked to the user's chosen source account
   - `scope.beneficiary_id`: locked to the user's chosen beneficiary
   - `scope.max_amount`: locked to the schedule's configured amount
   - `iss`: `"fund-transfer-service/scheduler"`
   - `aud`: `"internal/transfer-execution"`
   - `exp`: 30 days from creation

2. **Storage**: the delegated JWT is encrypted with AES-256 using a key held exclusively
   in the platform secret store (Azure Key Vault or equivalent). The encrypted ciphertext
   is stored in `transfer_schedules.delegated_jwt`. The encryption key is never written
   to source code, configuration files, or Git.

3. **At execution time** (no live session): the scheduler decrypts the JWT, verifies
   the signature and expiry, extracts `sub` and `scope`, and enforces all scope
   constraints before calling the fund transfer service. The fund transfer service
   validates the JWT as it would any authenticated request.

4. **Audit trail**: every execution audit log entry sets:
   `initiator = "system/scheduler (on behalf of user/{sub})"`.
   This makes the delegation explicit and queryable in compliance reviews.

5. **Expiry and renewal**: the delegated JWT expires after 30 days. When it expires,
   the schedule is automatically suspended and the user is notified to re-authenticate
   and renew. This forces periodic re-authorisation and catches revoked permissions or
   closed accounts.

---

## Zero Trust Evaluation (NIST SP 800-207)

| Zero Trust Principle | How This Decision Addresses It |
|----------------------|-------------------------------|
| Never trust, always verify | Delegated JWT is verified on every execution; no implicit system trust |
| Use least-privilege access | JWT scope is locked to one account, one beneficiary, one amount cap |
| Assume breach | Token expiry limits blast radius; compromise of one token doesn't expose other schedules |
| Verify explicitly | Signature, expiry, issuer, audience, and scope all validated before any fund movement |
| Authenticate every request | No ambient trust; each scheduler execution is independently authenticated |

**Zero Trust verdict**: This design satisfies NIST SP 800-207 for the scheduler
trust boundary. The scheduler is treated as an untrusted actor that must prove
its delegated authority on every operation.

---

## Consequences

### Positive
- Full audit traceability: user identity and scope are always known and recorded.
- Least-privilege execution: a compromised token can only affect one schedule's configured account and beneficiary.
- No ambient system trust: the scheduler cannot exceed the permissions the user granted at schedule creation.
- Forced re-authorisation: 30-day expiry ensures revoked permissions are caught within a bounded window.

### Negative / Trade-offs
- **Complexity at creation**: the schedule creation path must generate and encrypt a JWT, adding latency (mitigated: < 50 ms added to creation call).
- **Key management**: the encryption key must be rotated; all stored ciphertexts must be re-encrypted on rotation. Key rotation procedure must be documented and tested.
- **Re-authorisation friction**: users must log in again every 30 days to renew long-running schedules. Acceptable for a banking context; may be adjusted to 90 days after risk assessment.
- **Scope rigidity**: if the user wants to change the beneficiary or source account, they must cancel and recreate the schedule (the delegated JWT's scope is fixed). This is a deliberate security constraint, not a defect.

---

## Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|----------------|
| Ambient system user account | Grants blanket fund movement permission to any schedule; catastrophic if compromised |
| Stored user refresh token | Ties scheduler to upstream IdP availability; refresh token revocation not guaranteed |
| Per-execution user re-authentication | Requires user presence; impossible for autonomous execution by definition |
| OAuth2 client-credentials flow | Grants service-level trust (no user scoping); violates least-privilege for this use case |

---

## Review Trigger

This decision MUST be re-evaluated if:
- The scheduler is moved to a separate microservice (network boundary changes)
- The encryption key rotation interval changes
- Regulatory guidance changes regarding delegated financial authority
- The 30-day expiry is found to cause unacceptable user friction (adjust after risk assessment)
