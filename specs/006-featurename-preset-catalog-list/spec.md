# Feature Specification: Preset Catalog List

**Feature Branch**: `006-featurename-preset-catalog-list`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "preset catalog list"

## Overview

Users who want to browse all their saved transfer presets — without a specific preset name in mind — need a structured catalog view: a paginated, groupable list of every preset they own, displaying enough information to recognise and select one at a glance. Unlike Preset Search (spec 003), which is keyword and filter driven, the Preset Catalog List is the default browse experience: an always-available, organised inventory of all presets that a user can scan, sort, group, and act on. This is typically the first screen a user sees when they navigate to "My Presets".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse All Presets at a Glance (Priority: P1)

A user navigates to the "My Presets" section of the banking app. They see all their saved transfer presets displayed as a scrollable, paginated list — each entry showing the preset name, transfer type, beneficiary name, currency, and status. They scan the list and tap a preset to initiate a transfer, without needing to search or filter anything.

**Why this priority**: This is the core MVP of the feature. A user must be able to see all their presets before any grouping, sorting, or filtering capability adds value. Without this, no other story can be independently delivered.

**Independent Test**: A user with 10 saved presets navigates to the catalog; all 10 appear with correct name, type, beneficiary, currency, and status — fully testable without any filter or group functionality.

**Acceptance Scenarios**:

1. **Given** a user has 10 saved presets, **When** they open the Preset Catalog, **Then** all 10 are listed with name, transfer type, beneficiary reference, currency, and status (active/invalid) visible on each row.
2. **Given** a user has zero presets, **When** they open the Preset Catalog, **Then** an empty state is shown with a clear prompt to create their first preset.
3. **Given** a user has more than 20 presets, **When** they open the Preset Catalog, **Then** the first 20 are shown and pagination controls allow them to navigate to the next page.
4. **Given** a preset has an `INVALID` status, **When** it appears in the catalog, **Then** it is visually distinguished (e.g., marked with an invalid indicator) and the invalidity reason is accessible without leaving the list.

---

### User Story 2 - Group Presets by Transfer Type (Priority: P2)

A user who has both domestic fund transfer presets and FX transfer presets wants to see them separated into clearly labelled groups rather than mixed together. They toggle a "Group by Type" option and the catalog reorganises into sections — one per transfer type — each with its own header and item count.

**Why this priority**: Users with mixed preset types consistently report confusion when all types are interleaved. Grouping is a high-value UX improvement deliverable independently of sorting or other features.

**Independent Test**: A user with both domestic and FX presets enables "Group by Type"; verify two distinct sections appear, each containing only the correct preset type with accurate item counts.

**Acceptance Scenarios**:

1. **Given** a user has domestic and FX presets, **When** they enable "Group by Type", **Then** presets are displayed in two separate sections labelled "Fund Transfer" and "FX Transfer", each showing its item count.
2. **Given** grouping is active, **When** a user navigates to page 2, **Then** grouping headers persist and pagination applies within each group independently.
3. **Given** a user has only one transfer type, **When** they enable "Group by Type", **Then** a single group section is shown (not an empty second section).

---

### User Story 3 - Sort the Catalog (Priority: P2)

A user wants to find their most recently used presets at the top of the list. They select "Last Used" from a sort dropdown and the catalog reorders with the most recently used preset first. They can switch between sort options (name A–Z, creation date, last used) at any time without losing their place in the active group.

**Why this priority**: Sort order significantly affects how quickly a user locates a preset. "Last Used" sort mimics familiar patterns from contacts and recent-transactions lists in banking apps, directly reducing time-to-transfer.

**Independent Test**: A user applies "Last Used" sort; verify the list reorders with the most recently used preset at position 1 and results return within 500ms.

**Acceptance Scenarios**:

1. **Given** a user selects "Last Used" sort, **When** the catalog reloads, **Then** presets are ordered with the most recently used first; presets never used appear at the bottom ordered by creation date.
2. **Given** a user selects "Name A–Z" sort, **When** the catalog reloads, **Then** presets are ordered alphabetically by name, case-insensitive.
3. **Given** grouping and sort are both active, **When** the catalog renders, **Then** sort is applied within each group independently.

---

### User Story 4 - Act on a Preset Directly from the Catalog (Priority: P3)

A user sees a preset in the catalog and wants to initiate a transfer from it without navigating away. They tap an action button on the preset row and are taken directly to the transfer initiation form, pre-populated with that preset's values. They can also access rename, delete, and "mark as favourite" actions from the same row.

**Why this priority**: The catalog is most valuable when it reduces steps to action. Direct row-level actions eliminate the need to open a detail view before acting, materially reducing time-to-transfer.

**Independent Test**: From the catalog, tap "Use" on a preset row; verify the transfer initiation form opens pre-populated with the correct preset values, in under 2 seconds.

**Acceptance Scenarios**:

1. **Given** a user taps "Use" on an active preset, **When** the action is triggered, **Then** the transfer initiation form opens pre-populated with the preset's values within 2 seconds.
2. **Given** a user taps "Use" on an invalid preset, **When** the action is triggered, **Then** the transfer is blocked and the invalidity reason is displayed instead of opening the form.
3. **Given** a user taps "Delete" on a preset, **When** they confirm the deletion, **Then** the preset is removed from the catalog immediately and an undo option is offered for 5 seconds.
4. **Given** a user taps "Favourite" on a preset, **When** the action is confirmed, **Then** the preset is marked as a favourite and a "Favourites" group or sort option becomes available in the catalog.

---

### Edge Cases

- What happens when the catalog is loading and the user's network drops mid-page? → The page currently loaded remains visible; a connectivity warning is shown and a retry option appears for the next page load.
- What happens when a preset is deleted by another session while the user is browsing the catalog? → The deleted preset disappears from the catalog on the next page load or manual refresh; it does not cause an error on the current page.
- What happens when a user has exactly 200 presets (the per-user limit per spec 005)? → The catalog displays all 200; a banner informs the user they have reached the preset limit and must delete or archive before creating new ones.
- What happens when the "last used" timestamp is unavailable for some presets? → Those presets are sorted to the bottom of the "Last Used" view, ordered by creation date among themselves.
- What happens when a preset's beneficiary name is very long? → The name is truncated with an ellipsis in the list view; the full name is accessible in the row detail or tooltip.
- What happens when the user has only invalid presets? → The catalog shows all invalid presets with their status; the empty-state prompt for "create your first preset" does not appear since presets do exist.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display all of a user's presets (in all states except `PURGED`) in a paginated list, with a maximum of 20 presets per page.
- **FR-002**: Each list row MUST display at minimum: preset name, transfer type, beneficiary reference (masked account or alias), currency, and status badge (`ACTIVE`, `INVALID`, `ARCHIVED`).
- **FR-003**: The system MUST display an empty state when the user has no presets, including a clear call-to-action to create one.
- **FR-004**: The system MUST support grouping presets by transfer type (Fund Transfer / FX Transfer), with each group displaying its own header and item count.
- **FR-005**: The system MUST support the following sort options: Name A–Z, Name Z–A, Creation Date (newest first), Creation Date (oldest first), Last Used (most recent first).
- **FR-006**: Sort and grouping preferences MUST be remembered for the duration of the user's session; returning to the catalog within the same session restores the previously selected view.
- **FR-007**: The system MUST provide a row-level "Use" action on each active preset, navigating the user to the transfer initiation form pre-populated with that preset's values.
- **FR-008**: The system MUST provide row-level actions for: Delete (with confirmation and 5-second undo), Rename (inline), and Mark/Unmark as Favourite.
- **FR-009**: The system MUST visually distinguish invalid presets from active ones, and MUST display the invalidity reason on demand (e.g., via tooltip or expanded row) without leaving the catalog.
- **FR-010**: The system MUST support a "Favourites" group or sort dimension: presets marked as favourites MUST be surfaceable at the top of the list or in a dedicated section.
- **FR-011**: The system MUST return the catalog for a user with up to 200 presets within the defined performance threshold (see PERF-001).
- **FR-012**: The system MUST display a banner when the user has reached the 200-preset limit, preventing the "Create Preset" action until existing presets are deleted or archived.

### Security & Compliance Requirements *(mandatory for banking systems)*

- **SEC-001**: The catalog MUST only return presets belonging to the authenticated user; unauthenticated requests MUST be rejected, and cross-user access MUST be impossible by design.
- **SEC-002**: Beneficiary account numbers displayed in the catalog MUST be masked (last 4 digits only); full account numbers MUST NOT appear in list view.
- **SEC-003**: All row-level actions that mutate preset state (delete, rename, favourite) MUST be performed over authenticated, encrypted channels and MUST produce an audit log entry per spec 005.
- **SEC-004**: The delete action MUST require explicit user confirmation before execution to prevent accidental data loss.
- **SEC-005**: All catalog data MUST be transmitted over encrypted channels; the catalog page MUST NOT cache sensitive preset data in browser storage beyond the session lifetime.

### Data Integrity Requirements *(mandatory for financial features)*

- **DI-001**: The catalog MUST reflect the current persisted state of presets; results MUST NOT be served from a cache older than 5 seconds.
- **DI-002**: Row-level delete and rename actions MUST be atomic: the preset state change and corresponding audit log entry MUST succeed or fail together per spec 005.
- **DI-003**: The system MUST maintain an `audit_log` table containing at minimum: `operation_type` (controlled enum), `operation_id` (UUID), `initiator` (authenticated identity), `timestamp` (server-set TIMESTAMPTZ). The table MUST be append-only.
- **DI-004**: Every state-changing operation triggered from the catalog (delete, rename, favourite) MUST produce exactly one `audit_log` entry written within the same ACID transaction.
- **DI-005**: The undo action following a delete MUST restore the preset to its previous state atomically; a partial restore (preset visible but audit entry missing) MUST NOT occur.

### Performance Requirements

- **PERF-001**: The initial catalog page (first 20 presets) MUST load and render within 500ms (p95) for a user with up to 200 presets.
- **PERF-002**: Applying a sort or group change MUST produce an updated catalog view within 500ms (p95).
- **PERF-003**: Navigating to the next page of results MUST complete within 500ms (p95).
- **PERF-004**: The system MUST support at least 500 concurrent users loading the catalog without exceeding the 500ms (p95) threshold.

### Key Entities

- **Catalog View**: The paginated, optionally grouped and sorted presentation of a user's full preset inventory. Stateless from the server's perspective — all grouping and sort are applied at query time.
- **Preset Row**: A single entry in the catalog representing one preset, displaying summary fields and exposing row-level actions (Use, Delete, Rename, Favourite).
- **Group**: A labelled section within the catalog containing presets of a single transfer type (Fund Transfer or FX Transfer), with its own header and item count. Only present when grouping is enabled.
- **Favourite**: A user-assigned flag on a preset that elevates it in the catalog sort order or places it in a dedicated section. Persisted as a user preference per preset.
- **Catalog Preference**: The user's current session-scoped view settings: selected sort option, grouping on/off, current page. Restored on return to the catalog within the same session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users with up to 200 presets see their first catalog page fully rendered within 500ms (p95), measured under a 500-concurrent-user load.
- **SC-002**: 90% of users locate and act on a target preset from the catalog in under 60 seconds, without resorting to Preset Search, measured by task-completion studies post-launch.
- **SC-003**: Time-to-initiate-transfer (from catalog landing to pre-populated transfer form) is under 30 seconds for 90% of catalog-initiated transfers.
- **SC-004**: Zero incidents of a user seeing another user's presets in the catalog, verified by automated isolation tests on every deployment.
- **SC-005**: The delete-with-undo flow has a zero-error rate: every confirmed delete is reversible within the 5-second window with 100% success, verified by automated flow tests.
- **SC-006**: 100% of catalog-initiated state changes (delete, rename, favourite) produce a corresponding audit log entry, verified by reconciliation checks run daily.

## Assumptions

- Preset creation is handled by the Fund Transfer (spec 001) and FX Transfer (spec 002) features; the catalog is read-and-act only — it does not create new presets.
- The canonical preset data model and lifecycle rules defined in spec 005 (Preset Info Architecture Governance) are adopted before this feature is built; the catalog relies on that schema.
- The "Use" action hands off to the existing transfer initiation flows in spec 001 and spec 002; the catalog does not implement a new transfer form.
- "Favourite" is a new user preference field added to the preset data model under spec 005's schema evolution process; this spec assumes that addition is approved and implemented.
- The 200-preset-per-user limit is enforced by spec 005's governance rules; the catalog only needs to display the banner and disable the create action, not enforce the limit itself.
- Mobile native app support is out of scope for v1; the catalog targets web-based banking clients only.
- Archived presets (state `ARCHIVED`) are visible in the catalog but in a collapsed section or secondary tab; the detailed design of that section is deferred to implementation planning.
