# Feature Specification: Preset Search Architecture

**Feature Branch**: `004-featurename-preset-search-architecture`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "preset search architecture"

## Overview

The Preset Search feature (spec 003) defines *what* users can do when searching saved transfer presets. This specification defines the **system-level architecture** required to make that search experience reliable, secure, and scalable — describing the service structure, data ownership model, integration contracts between system components, and the quality attributes the architecture must satisfy. It is intentionally free of technology choices and written for architects, product managers, and senior engineers evaluating system design options.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Search Across All Entry Points (Priority: P1)

A user searching for a preset from the Fund Transfer screen and the same user searching from the FX Transfer screen both see the same result set — the system has a single authoritative source of preset data regardless of which product surface initiates the search. Users never encounter inconsistencies between entry points.

**Why this priority**: A fractured data model (presets owned separately by each transfer product) would create inconsistency and prevent the unified search experience. Establishing a single ownership model is the foundational architectural decision.

**Independent Test**: Can be fully tested by creating a preset via the Fund Transfer flow, then verifying it appears in search results when initiated from the FX Transfer flow, and vice versa.

**Acceptance Scenarios**:

1. **Given** a preset created through the Fund Transfer product, **When** the user searches from the FX Transfer entry point, **Then** the preset appears in results with correct type labelling.
2. **Given** a preset is updated (name changed), **When** the user searches from any entry point within 5 seconds, **Then** the updated name is reflected in results.
3. **Given** a preset is deleted, **When** the user searches from any entry point, **Then** the deleted preset does not appear in results.

---

### User Story 2 - Search Results Isolated Per User (Priority: P1)

No matter how the system is structured internally, each user sees only their own presets in search results. A system architecture failure that leaks one user's presets into another user's search results must be impossible by design — not just filtered at the application layer.

**Why this priority**: Data isolation is a hard security requirement. The architecture must enforce it structurally, not as an afterthought.

**Independent Test**: Can be fully tested by logging in as two different users, searching with identical terms, and confirming each user sees only their own presets.

**Acceptance Scenarios**:

1. **Given** two users with presets sharing identical names, **When** each user searches for that name, **Then** each sees only their own preset in results.
2. **Given** a user attempts to query another user's presets directly (e.g., by manipulating an identifier), **Then** the system rejects the request with an access-denied response.

---

### User Story 3 - Search Remains Available When Transfer Services Are Down (Priority: P2)

A user can still search their presets even if the Fund Transfer service or the FX Transfer execution service is temporarily unavailable. The search capability does not depend on the availability of downstream transaction processing services.

**Why this priority**: Search is a read-only discovery operation. Tying its availability to write-path services unnecessarily reduces reliability and frustrates users who simply want to view their presets.

**Independent Test**: Can be fully tested by disabling the transfer execution service and verifying that search results are still returned correctly.

**Acceptance Scenarios**:

1. **Given** the fund transfer execution service is unavailable, **When** a user searches for presets, **Then** search results are returned normally.
2. **Given** the search service itself has a partial failure affecting one data shard, **When** a user searches, **Then** a degraded-but-functional response is returned (partial results with a clear degradation notice) rather than a complete failure.

---

### User Story 4 - Preset Data Changes Reflected Promptly (Priority: P3)

When a user creates, renames, or deletes a preset, the change is reflected in subsequent search results within a defined time window. Users do not encounter stale data that causes confusion (e.g., searching for a renamed preset by its old name and finding it).

**Why this priority**: Data freshness directly impacts user trust. Stale results after a user-initiated change are a known source of support escalations.

**Independent Test**: Can be fully tested by modifying a preset and immediately performing a search, then measuring the elapsed time until results reflect the change.

**Acceptance Scenarios**:

1. **Given** a user renames a preset, **When** they search for the new name within 5 seconds, **Then** the renamed preset appears in results.
2. **Given** a user creates a new preset, **When** they immediately search for it by name, **Then** it appears in results within 5 seconds.

---

### Edge Cases

- What happens when the preset data store is briefly unavailable? → The search service returns a service-unavailable response with a retry-after hint; no partial or misleading results are served.
- What happens when the total number of presets across all users grows to tens of millions? → The architecture must support horizontal scaling of search capacity without schema changes or downtime.
- What happens when two users simultaneously modify and search for the same preset (multi-device scenario for a shared family account)? → The system applies last-write-wins semantics and returns the most recently committed state.
- What happens when a search request exceeds the timeout threshold? → The request fails fast with a timeout response; no partial result is cached as authoritative.
- What happens when the audit log write fails during a search? → The search result is not returned; the operation is aborted and an error is surfaced to the caller (audit integrity over availability for logged operations).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain a single, unified preset data store shared by all transfer products (fund transfer, FX transfer); presets MUST NOT be siloed per product.
- **FR-002**: The system MUST expose a dedicated search capability as an independently deployable component, decoupled from the transfer execution path.
- **FR-003**: The search component MUST accept the following query parameters: keyword (free text), currency filter (one or more values), transfer type filter, sort field, sort direction, and page number.
- **FR-004**: The system MUST enforce user-scoped data isolation at the data access layer, not solely at the application layer.
- **FR-005**: The search component MUST remain operational and serve results even when fund transfer or FX transfer execution services are unavailable.
- **FR-006**: The system MUST guarantee that preset data changes (create, update, delete) are reflected in search results within 5 seconds.
- **FR-007**: The system MUST provide a versioned, documented contract for the search capability so that all consuming surfaces (web, future mobile) can integrate without coupling to internal data structures.
- **FR-008**: The search component MUST emit structured operational events (query received, result count, latency) consumable by the platform's monitoring system.
- **FR-009**: The system MUST support graceful degradation: if a non-critical subsystem (e.g., usage-tracking for "last used" sort) is unavailable, search MUST still return results using available data.
- **FR-010**: The system MUST support addition of new filter dimensions (e.g., filter by beneficiary country) without requiring changes to existing consumer integrations.

### Security & Compliance Requirements *(mandatory for banking systems)*

- **SEC-001**: All requests to the search capability MUST be authenticated; unauthenticated requests MUST be rejected before any data access occurs.
- **SEC-002**: User identity established at authentication MUST be propagated through every internal service call in the search path; no service in the chain may accept an unverified user identity claim.
- **SEC-003**: The search component MUST log every query to the audit log including: authenticated user identity, query parameters, result count, and server timestamp — written atomically with the query execution.
- **SEC-004**: Account numbers and other sensitive identifiers within preset records MUST be masked before inclusion in search responses; the search component MUST never return raw account numbers to consumers.
- **SEC-005**: The internal data channel between the search component and the preset data store MUST be encrypted in transit.
- **SEC-006**: The search component's contract (API) MUST be versioned; breaking changes to the security model (e.g., changes to authentication scope) MUST increment the major version.

### Data Integrity Requirements *(mandatory for financial features)*

- **DI-001**: The preset data store MUST be the single source of truth for all preset data; no secondary copy of preset data used for search may diverge from the primary store beyond the 5-second freshness SLA.
- **DI-002**: Preset records MUST carry a monotonically increasing version stamp so that search results can be validated against the expected state by consumers when required.
- **DI-003**: The system MUST maintain an `audit_log` table containing at minimum: `operation_type` (controlled enum), `operation_id` (UUID), `initiator` (authenticated identity), `timestamp` (server-set TIMESTAMPTZ). The table MUST be append-only.
- **DI-004**: Audit log entries for search operations MUST be written within the same transactional boundary as the search execution; if the audit write fails, the search response MUST not be returned.
- **DI-005**: The architecture MUST prevent any component from issuing UPDATE or DELETE operations against the audit log; this constraint MUST be enforced at the data store level where technically feasible.

### Performance Requirements

- **PERF-001**: Search query results MUST be returned to the consumer within 500ms (p95) for preset collections of up to 1,000 records per user.
- **PERF-002**: Filter and sort changes applied to an existing result set MUST produce updated results within 500ms (p95).
- **PERF-003**: The search architecture MUST sustain at least 500 concurrent search requests without degradation in response time.
- **PERF-004**: The architecture MUST support horizontal scale-out to handle 10× the baseline load without schema or contract changes.
- **PERF-005**: Preset data changes MUST propagate to search-visible state within 5 seconds under normal operating conditions.

### Key Entities

- **Preset Data Store**: The authoritative, shared repository of all user transfer presets. Serves as the single source of truth for preset create/update/delete operations and the origin of data consumed by the search component.
- **Search Component**: The independently deployable service responsible for accepting search queries, applying filters and sort, enforcing user scoping, and returning paginated preset results. It reads from the Preset Data Store and emits audit log entries.
- **Search Contract**: The versioned, documented interface definition governing how consumers (web application, future mobile clients) interact with the Search Component. Includes query parameters, response schema, error codes, and authentication requirements.
- **Audit Log**: The append-only record of all operations (including search queries) across the system, satisfying regulatory and compliance traceability requirements.
- **Usage Tracker**: An optional, non-critical component that records "last used" timestamps per preset per user to support "Last Used" sort in search results. Its unavailability MUST NOT prevent search from functioning.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of search queries return results within 500ms end-to-end as experienced by the consumer, validated under a load of 500 concurrent users.
- **SC-002**: Preset data changes are reflected in search results within 5 seconds in 99% of cases under normal operating conditions.
- **SC-003**: Zero incidents of one user's preset data appearing in another user's search results, verified by automated isolation tests run on every deployment.
- **SC-004**: Search availability remains at or above 99.9% even when the fund transfer or FX transfer execution services experience downtime, measured over a 30-day rolling window.
- **SC-005**: The search architecture scales to 10× baseline concurrent load without requiring structural changes, verified by load testing before production release.
- **SC-006**: 100% of search operations produce a corresponding audit log entry; zero silent audit failures are permitted, verified by reconciliation checks.
- **SC-007**: Adding a new filter dimension to the search contract requires zero changes to existing consumer integrations, validated by contract compatibility tests.

## Assumptions

- The Preset Search feature (spec 003) is the primary consumer of this architecture; all user-facing behaviour is specified there and not repeated here.
- Both the Fund Transfer Service (spec 001) and the FX Transfer service (spec 002) will write presets to the shared Preset Data Store as part of their respective implementations; this architectural spec does not cover how those write paths are built.
- A platform-level authentication and identity propagation mechanism already exists and will be reused; this spec does not define a new authentication system.
- The platform already has a structured logging and monitoring infrastructure; the search component emits events in a format compatible with that infrastructure.
- "Horizontal scale-out" is achievable within the platform's existing deployment model; this spec does not require a change in deployment paradigm.
- The Usage Tracker (for "last used" sort) is a net-new component introduced by this architecture; its detailed specification is deferred to the implementation planning phase.
- Mobile client support is out of scope for v1; the versioned Search Contract must be designed to accommodate it in a future iteration without breaking changes.
