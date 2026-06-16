# Feature Specification: Preset Search

**Feature Branch**: `003-featurename-preset-search`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "preset search"

## Overview

Authenticated banking users accumulate saved transfer presets over time (e.g., "Monthly rent to landlord", "Weekly salary to John"). As the list grows, locating the right preset before initiating a transfer becomes slow and error-prone. This feature provides a fast, filtered search experience over a user's saved transfer presets, reducing the time from intent to transfer initiation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find Preset by Name (Priority: P1)

A retail banking user has dozens of saved transfer presets and wants to quickly find a specific one by typing part of its name. They type "rent" in the search field and immediately see all presets whose name or description contains that keyword, then select one to initiate the transfer.

**Why this priority**: This is the core value of the feature. Without keyword search, all other filtering is moot. It delivers an immediately usable MVP for any user with more than a handful of presets.

**Independent Test**: Can be fully tested by entering a search term and verifying that only matching presets are returned — delivers the primary value of rapid preset discovery.

**Acceptance Scenarios**:

1. **Given** a user has 20 saved presets, **When** they search for "rent", **Then** only presets whose name or description contains "rent" (case-insensitive) are displayed.
2. **Given** no presets match the search term, **When** the user searches for "xyz123", **Then** an empty state message is shown ("No presets match your search").
3. **Given** a user clears the search field, **When** the field becomes empty, **Then** all presets are displayed again.

---

### User Story 2 - Filter Presets by Currency (Priority: P2)

A user who makes both EUR and USD transfers wants to narrow their preset list to only EUR presets before searching by name. They select "EUR" from a currency filter and the list updates instantly.

**Why this priority**: Currency is a primary dimension that divides users' preset collections (especially after the FX transfer feature). Filtering by currency prevents confusion and reduces the result set before name-searching.

**Independent Test**: Can be fully tested by applying a currency filter without a search term, verifying only presets for that currency appear.

**Acceptance Scenarios**:

1. **Given** a user has EUR and USD presets, **When** they select "EUR" from the currency filter, **Then** only EUR presets are shown.
2. **Given** a currency filter is active, **When** the user also types a search term, **Then** results are filtered by both currency AND keyword simultaneously.
3. **Given** a currency filter is active, **When** the user clears the filter, **Then** all currencies are shown again.

---

### User Story 3 - Filter Presets by Transfer Type (Priority: P3)

A user wants to distinguish between standard domestic transfer presets and FX (foreign currency) transfer presets. They select "FX Transfer" from a type filter to see only cross-currency presets.

**Why this priority**: As the platform supports both fund transfers and FX transfers, users may need to segregate them. This filter helps power users manage large preset collections.

**Independent Test**: Can be fully tested by filtering by transfer type and verifying only presets of that type appear.

**Acceptance Scenarios**:

1. **Given** a user has both domestic and FX transfer presets, **When** they filter by "FX Transfer", **Then** only FX transfer presets are shown.
2. **Given** a type filter is active, **When** combined with a currency filter and keyword search, **Then** all three constraints are applied simultaneously.

---

### User Story 4 - Sort and Paginate Results (Priority: P4)

A user wants to sort their filtered results by most recently used, so their frequently used presets appear at the top. They select "Last Used" from a sort dropdown and browse through paginated results.

**Why this priority**: Sorting and pagination are secondary to finding the right preset, but critical for usability with large preset collections (50+ presets).

**Independent Test**: Can be fully tested by verifying sort order changes correctly with each sort option, and that pagination controls navigate between pages of results.

**Acceptance Scenarios**:

1. **Given** search results contain 30 presets, **When** "Last Used" sort is selected, **Then** presets are ordered with the most recently used first.
2. **Given** more than 20 results exist, **When** the results are displayed, **Then** pagination controls appear and allow navigation through all results.
3. **Given** the user is on page 2, **When** they change the sort order, **Then** they are returned to page 1 of the newly sorted results.

---

### Edge Cases

- What happens when a user has zero saved presets? → Empty state is shown with a call-to-action to create a preset.
- What happens when the search term contains special characters (e.g., `%`, `*`, SQL injection attempts)? → Input is sanitised; the system treats special characters as literals and returns safe results.
- What happens when the search service is temporarily unavailable? → A user-friendly error is shown; the user can retry without losing their search input.
- What happens when a preset is deleted by another session while the user is viewing search results? → The deleted preset is excluded from subsequent searches; if the user tries to select it, a clear "Preset no longer available" message is shown.
- What happens when a user has more than 1,000 presets? → Results are always paginated; performance targets still apply.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow authenticated users to search their own saved transfer presets by keyword (matched against preset name and description, case-insensitive).
- **FR-002**: System MUST return only presets belonging to the authenticated user; presets from other users MUST never appear in results.
- **FR-003**: System MUST support filtering search results by currency (one or more currencies selected simultaneously).
- **FR-004**: System MUST support filtering search results by transfer type (domestic fund transfer, FX transfer, or both).
- **FR-005**: System MUST support sorting results by: preset name (A–Z / Z–A), creation date (newest/oldest), and last-used date (most/least recent).
- **FR-006**: System MUST paginate search results, returning a maximum of 20 presets per page.
- **FR-007**: System MUST return an empty result set (not an error) when no presets match the applied filters and keyword.
- **FR-008**: System MUST allow a user to select a preset from search results and proceed directly to the transfer initiation flow pre-populated with that preset's values.
- **FR-009**: System MUST sanitise all search inputs to prevent injection attacks before processing.
- **FR-010**: System MUST display the total count of matching presets alongside the paginated results.

### Security & Compliance Requirements *(mandatory for banking systems)*

- **SEC-001**: System MUST authenticate all search requests; unauthenticated requests MUST be rejected with a 401 response.
- **SEC-002**: System MUST enforce authorisation so that a user can only retrieve their own presets; any attempt to access another user's presets MUST be rejected with a 403 response.
- **SEC-003**: System MUST log all search queries to the audit log, capturing: authenticated user identity, search parameters supplied, result count returned, and timestamp.
- **SEC-004**: Preset data returned in search results MUST not expose raw account numbers in full; account numbers MUST be masked (e.g., last 4 digits only) in the search results list view.
- **SEC-005**: All search API requests and responses MUST be transmitted over encrypted channels.

### Data Integrity Requirements *(mandatory for financial features)*

- **DI-001**: Search results MUST reflect the current persisted state of presets; stale or cached results older than 5 seconds MUST not be served.
- **DI-002**: The search feature is read-only; it MUST NOT modify preset data in any way.
- **DI-003**: System MUST maintain an `audit_log` table containing at minimum: `operation_type` (controlled enum), `operation_id` (UUID), `initiator` (authenticated identity), `timestamp` (server-set TIMESTAMPTZ). The table MUST be append-only.
- **DI-004**: Every audit log entry for a search operation MUST be written atomically; if the audit write fails, the search operation MUST return an error rather than silently skip auditing.

### Performance Requirements

- **PERF-001**: Search query results MUST be returned in under 500ms (p95) for up to 1,000 presets per user.
- **PERF-002**: Applying or changing a filter or sort option MUST produce updated results in under 500ms (p95).
- **PERF-003**: The search feature MUST support at least 500 concurrent search requests without degradation in response time.

### Key Entities

- **Transfer Preset**: A saved, named configuration for a transfer, including recipient details, amount (optional), currency, and transfer type (domestic or FX). Owned by a single user. Has a creation date and a last-used date.
- **Search Query**: The set of parameters a user submits — keyword, currency filter(s), transfer type filter, sort field, sort direction, and page number. Not persisted; ephemeral per request.
- **Search Result**: A paginated list of Transfer Presets matching the query, along with total count and pagination metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can locate a known preset by name within 30 seconds, including time to type the search term and view results.
- **SC-002**: 95% of search queries return results in under 500ms end-to-end as measured from the user's perspective.
- **SC-003**: 90% of users successfully find and select the correct preset on their first search attempt without needing to refine their query.
- **SC-004**: The feature handles at least 500 concurrent users performing searches without any user experiencing a timeout or error.
- **SC-005**: Zero incidents of a user seeing another user's preset data in search results.
- **SC-006**: Time-to-initiate-transfer (from landing on the preset search screen to reaching the pre-populated transfer form) is under 60 seconds for 90% of users.

## Assumptions

- Users already have saved transfer presets in the system (created via the Fund Transfer Service or FX Transfer feature). Preset creation is out of scope for this feature.
- A user's preset collection may grow up to 1,000 entries; beyond this, archiving or deletion is handled by a separate feature.
- The existing authentication and session management system will be reused without modification.
- Preset names and descriptions are stored in plain text and are short enough (under 200 characters each) to support efficient keyword matching.
- Mobile platform support (native apps) is out of scope for v1; the feature targets web-based banking clients only.
- The transfer initiation flow (pre-populated from a selected preset) already exists in the Fund Transfer Service and FX Transfer features; this feature only needs to hand off the selected preset data to that existing flow.
- Keyword search matches the preset name and description fields only; it does not search recipient account numbers or other financial identifiers.
