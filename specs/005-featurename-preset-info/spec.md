# Feature Specification: Preset Info Architecture Governance

**Feature Branch**: `005-featurename-preset-info`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "preset info architecture-governance"

## Overview

Transfer presets are created through multiple product surfaces (Fund Transfer, FX Transfer) and consumed by the Preset Search feature. Without a governing standard for what a preset *is* — its canonical fields, lifecycle rules, access policies, versioning, and retention obligations — each product team risks defining presets differently, leading to data inconsistency, search failures, compliance gaps, and brittle integrations. This specification establishes the **governance model for preset information**: the authoritative definition of preset data, the rules governing its lifecycle, and the policies all system components must adhere to when creating, reading, updating, or retiring presets.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preset Created in One Product Appears Correctly in Another (Priority: P1)

A user saves a transfer preset via the Fund Transfer product. They then open the FX Transfer product and browse their saved presets. The preset appears with all expected fields correctly populated — no missing labels, no blank amounts, no unrecognised types. The governance model ensures every product writes the same canonical data so every consuming surface reads it correctly.

**Why this priority**: This is the foundational correctness guarantee. If presets written by one product cannot be read correctly by another, the shared data model has failed at its most basic function.

**Independent Test**: Create a preset via the Fund Transfer product; verify it appears with a complete, correct field set in the FX Transfer preset list and Preset Search results.

**Acceptance Scenarios**:

1. **Given** a preset created via the Fund Transfer product, **When** it is displayed in any other product surface, **Then** all mandatory fields (name, transfer type, currency, beneficiary reference) are present and correctly labelled.
2. **Given** a preset with an optional field omitted (e.g., no saved amount), **When** it is displayed in any surface, **Then** the field is shown as empty/unset — no error, no placeholder, no default value substituted.
3. **Given** a preset created before the governance standard was in effect, **When** it is read by any surface, **Then** the system applies defined migration rules to bring it into compliance rather than failing.

---

### User Story 2 - Preset Lifecycle Events Are Fully Traceable (Priority: P1)

A compliance officer needs to audit who created, modified, and deleted a specific preset as part of a fraud investigation. The governance model mandates that every lifecycle event (creation, update, deletion, archiving) produces a complete, immutable audit record with the actor identity, timestamp, and before/after state — making the full lifecycle of any preset reconstructible from the audit log.

**Why this priority**: Regulatory and fraud-detection requirements demand complete traceability of financial configuration data. Gaps in lifecycle auditing are a compliance failure.

**Independent Test**: Perform a full preset lifecycle (create → update name → delete); verify the audit log contains three entries with correct operation types, actor identities, and timestamps, and that the before/after state is captured for the update.

**Acceptance Scenarios**:

1. **Given** a preset is created, **When** the operation completes, **Then** the audit log contains an entry with `operation_type = PRESET_CREATED`, the creator's identity, and the full initial field set.
2. **Given** a preset is updated (e.g., name changed), **When** the operation completes, **Then** the audit log contains an entry with `operation_type = PRESET_UPDATED`, the modifier's identity, and both the previous and new values of the changed fields.
3. **Given** a preset is deleted, **When** the operation completes, **Then** the audit log contains an entry with `operation_type = PRESET_DELETED`, the deleting actor's identity, and a snapshot of the preset's final state before deletion.
4. **Given** an audit log entry has been written, **When** any actor attempts to modify or delete it, **Then** the system rejects the operation.

---

### User Story 3 - Stale or Invalid Presets Are Governed, Not Silently Broken (Priority: P2)

A user's beneficiary account has been closed. The preset that referenced it is now technically invalid. Rather than silently surfacing a broken preset in search results, the governance model defines a clear "invalid" state with a mandatory reason code. Users see the preset marked as invalid with an explanation, and operators can query and act on all invalid presets without needing custom tooling.

**Why this priority**: Invalid presets that appear usable are a source of failed transfers, user frustration, and potential financial harm. A governed invalid state prevents silent failures.

**Independent Test**: Mark a preset as invalid with a reason code; verify it appears in search results with a visible invalid status and reason, and that attempting to initiate a transfer from it is blocked with a clear explanation.

**Acceptance Scenarios**:

1. **Given** a preset is marked invalid (e.g., beneficiary account closed), **When** it appears in search results, **Then** it is clearly labelled as invalid with the reason code displayed.
2. **Given** an invalid preset, **When** a user attempts to initiate a transfer from it, **Then** the system blocks the attempt and presents the reason for invalidity.
3. **Given** a preset is resolved (e.g., beneficiary account updated), **When** the preset is restored to valid state, **Then** the audit log records the state transition and reason.

---

### User Story 4 - Preset Data Is Retained and Purged According to Policy (Priority: P3)

An operations team member needs to confirm that user preset data is retained for the mandatory regulatory period and purged thereafter. The governance model defines explicit retention periods per preset state (active, deleted, archived) and mandates that purging is logged — giving the operations team a verifiable, auditable data lifecycle.

**Why this priority**: GDPR and banking data retention regulations impose legal obligations. Unmanaged retention (keeping data forever or purging too early) creates regulatory risk.

**Independent Test**: Set a preset to deleted state; verify it is retained for the defined retention period, then purged with an audit entry, and is no longer accessible via any API after purge.

**Acceptance Scenarios**:

1. **Given** a preset in deleted state, **When** its retention period expires, **Then** the system purges it from the data store and records a `PRESET_PURGED` audit entry.
2. **Given** a purge event, **When** an actor queries the preset by its original identifier, **Then** the system returns a "not found" response — not the purged data.
3. **Given** an active preset belonging to a user who invokes "right to be forgotten", **When** the deletion is processed, **Then** the preset is marked for immediate purge and the audit entry records the GDPR basis for deletion.

---

### Edge Cases

- What happens when a product writes a preset with a field the governance model does not recognise? → Unrecognised fields are rejected at the write boundary with a validation error; products must not extend the preset schema unilaterally.
- What happens when two product surfaces attempt to update the same preset simultaneously? → Last-write-wins with optimistic concurrency control; the losing writer receives a conflict response and must re-read before retrying.
- What happens when a mandatory field is absent in a legacy preset? → The system applies the defined default for that field, records a `PRESET_MIGRATED` audit entry, and flags the preset for review.
- What happens when the audit log is full or unavailable during a lifecycle operation? → The lifecycle operation is rolled back; no preset state change is committed without a corresponding audit entry.
- What happens when a user has more presets than the defined per-user limit? → New preset creation is blocked with a clear limit-reached message; the user must archive or delete existing presets before creating new ones.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define and enforce a canonical preset schema: a fixed set of mandatory and optional fields applicable to all preset types (domestic transfer, FX transfer), with explicit field names, value constraints, and nullability rules.
- **FR-002**: All system components that create or update presets MUST validate preset data against the canonical schema before persisting; non-conforming writes MUST be rejected with a descriptive error.
- **FR-003**: The system MUST maintain a controlled vocabulary of preset states: `ACTIVE`, `INVALID`, `DELETED`, `ARCHIVED`, `PURGED`. State transitions MUST follow defined rules (e.g., `ACTIVE → INVALID`, `DELETED → PURGED`); invalid transitions MUST be rejected.
- **FR-004**: Every preset lifecycle operation (create, update, state transition, purge) MUST produce an audit log entry within the same transaction, capturing: operation type, actor identity, timestamp, and a snapshot of changed fields (before and after values for updates).
- **FR-005**: The system MUST enforce a per-user preset limit (default: 200 active presets); attempts to create beyond the limit MUST be rejected with a clear reason.
- **FR-006**: The system MUST support preset versioning: each write to a preset increments a version counter; consumers MAY use the version to detect and handle concurrent modification.
- **FR-007**: The system MUST define and enforce data retention periods per preset state: active presets retained for the life of the user account; deleted presets retained for 7 years from deletion date (regulatory minimum); purged presets leave only an audit trail.
- **FR-008**: The system MUST provide a governed purge process: purging MUST be triggered by policy (retention period expiry or GDPR right-to-be-forgotten request), MUST produce a `PRESET_PURGED` audit entry, and MUST make the preset data inaccessible via all APIs.
- **FR-009**: The system MUST support schema evolution governance: new optional fields may be added to the canonical schema without a breaking change; removing or renaming fields or changing a field from optional to mandatory MUST be treated as a breaking change and require a versioned migration path.
- **FR-010**: The system MUST expose a read-only governance report: a queryable view of preset counts by state and type, per user, for operational and compliance monitoring — accessible only to authorised operators.

### Security & Compliance Requirements *(mandatory for banking systems)*

- **SEC-001**: Write access to preset data (create, update, state transition) MUST be restricted to authenticated system components operating on behalf of an authenticated user; no anonymous or system-initiated writes are permitted without explicit authorisation.
- **SEC-002**: The governance report (FR-010) MUST be restricted to authorised operators; end users MUST NOT be able to access aggregate data about other users' presets.
- **SEC-003**: Preset audit log entries MUST NOT contain raw account numbers, PINs, or other high-sensitivity financial identifiers; such values MUST be masked or tokenised before logging.
- **SEC-004**: The purge process MUST comply with GDPR Article 17 (right to erasure): user-requested deletions MUST be processed within 30 days, and the purge audit entry MUST record the legal basis.
- **SEC-005**: All inter-service communication involving preset data MUST be authenticated and encrypted in transit; unauthenticated reads or writes MUST be rejected at the service boundary.
- **SEC-006**: The canonical schema and controlled state vocabulary MUST be versioned and stored in a governed artefact repository; changes MUST be approved before deployment.

### Data Integrity Requirements *(mandatory for financial features)*

- **DI-001**: All preset lifecycle operations MUST be atomic: a write to the preset data store and its corresponding audit log entry MUST succeed or fail together; partial commits are not permitted.
- **DI-002**: Preset version counters MUST be monotonically increasing and server-assigned; client-supplied version values MUST NOT be trusted for increment.
- **DI-003**: The system MUST maintain an `audit_log` table containing at minimum: `operation_type` (controlled enum), `operation_id` (UUID), `initiator` (authenticated identity), `timestamp` (server-set TIMESTAMPTZ). The table MUST be append-only.
- **DI-004**: The controlled `operation_type` vocabulary for preset operations MUST include at minimum: `PRESET_CREATED`, `PRESET_UPDATED`, `PRESET_INVALIDATED`, `PRESET_RESTORED`, `PRESET_DELETED`, `PRESET_ARCHIVED`, `PRESET_PURGED`, `PRESET_MIGRATED`. No values outside this vocabulary are permitted in the audit log.
- **DI-005**: Every state-changing operation MUST produce exactly one `audit_log` entry written within the same ACID transaction. Operations that cannot write their audit entry MUST be rolled back.
- **DI-006**: Legacy presets that pre-date the governance standard MUST be migrated to the canonical schema; migration MUST be non-destructive (original data preserved in audit trail) and produce a `PRESET_MIGRATED` entry per preset.

### Performance Requirements

- **PERF-001**: Preset schema validation at write time MUST add no more than 50ms (p95) to the total write operation latency.
- **PERF-002**: The governance report (FR-010) MUST return results within 2 seconds (p95) for datasets of up to 10 million presets.
- **PERF-003**: The retention purge process MUST operate as a background job and MUST NOT impact the response time of user-facing read or write operations.

### Key Entities

- **Canonical Preset Schema**: The authoritative, versioned definition of all fields a preset may contain — their names, types, mandatory/optional status, value constraints, and nullability rules. Shared across all products and enforced at all write boundaries.
- **Preset State Machine**: The defined set of valid preset states (`ACTIVE`, `INVALID`, `DELETED`, `ARCHIVED`, `PURGED`) and the permitted transitions between them, including the conditions and actors authorised to trigger each transition.
- **Preset Version**: A monotonically increasing counter assigned to each preset, incremented on every write. Enables consumers to detect concurrent modification and supports optimistic concurrency control.
- **Retention Policy**: The per-state rules governing how long preset data is kept before purging, the trigger conditions for purging, and the required audit trail left after purge.
- **Governance Report**: A read-only, operator-accessible view of preset population metrics (counts by state, type, and user) used for operational oversight and compliance reporting.
- **Schema Evolution Record**: The versioned changelog of additions, deprecations, and breaking changes to the Canonical Preset Schema, stored in a governed artefact repository and referenced by migration logic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of preset write operations across all products pass canonical schema validation before persistence; zero non-conforming presets are written to the data store, measured by automated schema conformance tests run on every deployment.
- **SC-002**: 100% of preset lifecycle operations (create, update, delete, archive, purge) produce a corresponding audit log entry; zero silent lifecycle events occur, verified by reconciliation checks run daily.
- **SC-003**: Zero incidents of preset data written by one product being unreadable or incorrectly rendered by another product surface, measured over a 90-day post-launch period.
- **SC-004**: All user-requested data deletions (GDPR right-to-be-forgotten) are processed and audit-logged within 30 days of request, with a 100% completion rate.
- **SC-005**: The governance report returns results in under 2 seconds for a dataset of 10 million presets, verified by load testing before production release.
- **SC-006**: Adding a new optional field to the canonical preset schema requires zero changes to existing product surfaces or consumers, validated by contract compatibility tests on every schema change.
- **SC-007**: The per-user preset limit (200 active) is enforced with zero exceptions; any attempt to exceed the limit is blocked and logged, verified by automated boundary tests.

## Assumptions

- The canonical preset schema defined by this governance spec will be adopted by the Fund Transfer Service (spec 001) and FX Transfer service (spec 002) retroactively; a migration plan for existing presets is required but its detailed design is deferred to implementation planning.
- A governed artefact repository (e.g., a schema registry or versioned configuration store) already exists on the platform or will be provisioned as part of this governance initiative.
- The 200 active-preset-per-user limit is a starting default; product and compliance teams may adjust it via a governed configuration change without a code release.
- The 7-year retention period for deleted presets reflects the minimum regulatory requirement applicable to this banking domain; jurisdiction-specific rules may require longer retention and must be configurable per user residency.
- "Right to be forgotten" requests are routed to this system via an existing GDPR compliance workflow; this spec does not define that workflow but requires the system to expose a purge trigger that the workflow can invoke.
- Legacy presets (pre-governance) are assumed to be a bounded, known population; an unbounded legacy migration would require a separate project scoping exercise.
- The governance report is consumed by internal operators only; no external regulatory reporting interface is in scope for v1.
