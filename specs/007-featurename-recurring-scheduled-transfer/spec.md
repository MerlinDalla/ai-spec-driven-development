# Feature Specification: Recurring Scheduled Transfer

**Feature Branch**: `007-featurename-recurring-scheduled-transfer`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "User can define a recurring, scheduled money transfer with an interval and end date"

## Architecture Governance Notes

> *Required by the architecture-governance preset. Documents N/A decisions with rationale.*

- **Memory-safe language constraints**: N/A at spec phase — no runtime or hardware choice is made here.
- **Trust boundaries affected**: (1) User ↔ Platform at schedule creation/modification (authentication boundary); (2) Platform ↔ Scheduling Engine at automated execution time (delegated identity boundary — user is absent); (3) Scheduling Engine ↔ Payment Execution at fund movement (privilege boundary).
- **Threat modeling**: STRIDE applies. Key threats: Tampering (schedule modified without user knowledge), Repudiation (user denies authorising a schedule), Elevation of Privilege (scheduler executing with excess permissions), DoS (flooding the schedule queue). Full STRIDE threat model to be produced at planning phase.
- **S-ADR required**: Yes — the introduction of an automated, user-absent financial execution subsystem is architecturally significant. S-ADR to be created at planning phase covering delegated identity, scheduler trust model, and failure handling.
- **Zero Trust**: Applies — the scheduler executes fund transfers without real-time user presence. It MUST carry verified delegated user identity per operation, not rely on implicit system-level trust.

## Overview

Banking users frequently need to make the same transfer repeatedly — rent, savings contributions, loan repayments, subscriptions — and manually initiating each transfer is error-prone and time-consuming. This feature allows an authenticated user to define a recurring, scheduled money transfer: specifying the amount, beneficiary, interval (e.g., weekly, monthly), start date, and end date. The system then executes the transfer automatically on each scheduled date until the end date is reached or the user cancels the schedule. Users retain full visibility and control — they can pause, modify, or cancel a schedule at any time.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a Recurring Transfer Schedule (Priority: P1)

An authenticated user wants to pay their monthly rent automatically. They navigate to "Scheduled Transfers", fill in the beneficiary, amount, currency, start date, interval (monthly), and end date, then confirm the schedule. The system validates the setup, displays a summary of all future execution dates, and activates the schedule. The user receives a confirmation.

**Why this priority**: Schedule creation is the foundational action. Without it, no other story can exist. It is the minimum deliverable that provides user value.

**Independent Test**: A user creates a monthly schedule; verify it is stored, the first execution date is correct, all future dates are listed, and a confirmation is shown — independently of execution.

**Acceptance Scenarios**:

1. **Given** an authenticated user with a valid source account, **When** they define a schedule (beneficiary, amount, currency, interval: monthly, start: first of next month, end: 12 months later), **Then** the schedule is saved, all 12 execution dates are shown in the confirmation summary, and the schedule status is `ACTIVE`.
2. **Given** a user submits a schedule with an end date before the start date, **When** they attempt to confirm, **Then** the system rejects the input with a clear validation message before any data is saved.
3. **Given** a user submits a schedule with an amount exceeding their account's daily transfer limit, **When** they attempt to confirm, **Then** the system rejects the schedule with an explanation that the per-execution amount exceeds the applicable limit.
4. **Given** a user defines a schedule with a start date in the past, **When** they attempt to confirm, **Then** the system rejects the input and prompts them to select a future start date.

---

### User Story 2 - View and Manage Existing Schedules (Priority: P1)

A user wants to see all their active recurring schedules — what amount goes where, on which dates, and when each schedule ends. They navigate to "Scheduled Transfers" and see a list of all their schedules with next execution date, remaining occurrences, and status. They can pause, resume, modify, or cancel any schedule from this list.

**Why this priority**: Without visibility and control, users cannot trust the system with their money. Management capability is inseparable from creation in terms of business value.

**Independent Test**: With one active schedule, navigate to the schedule list; verify name, amount, next execution date, remaining occurrences, and status all display correctly — independently of transfer execution.

**Acceptance Scenarios**:

1. **Given** a user has 3 active schedules, **When** they view the schedule list, **Then** each entry shows: beneficiary name, amount, currency, interval, next execution date, number of remaining executions, and status.
2. **Given** a user pauses an active schedule, **When** the next scheduled execution date passes, **Then** no transfer is executed and the schedule remains in `PAUSED` state with the next execution date unchanged.
3. **Given** a user cancels a schedule, **When** they confirm cancellation, **Then** the schedule moves to `CANCELLED` state, no future transfers are executed, and the cancellation is recorded in the audit log.
4. **Given** a user modifies the amount on an active schedule, **When** the change is saved, **Then** the new amount applies from the next pending execution date forward; already-executed transfers are unaffected.

---

### User Story 3 - Receive Notifications for Schedule Executions (Priority: P2)

A user wants to know when a scheduled transfer has been executed, failed, or is about to execute. They receive a notification (in-app and optionally email) for each execution event — success, failure, and an advance reminder — so they are always informed about automated movements of their money.

**Why this priority**: Users must be able to trust automated transfers. Notifications are the primary mechanism by which users maintain awareness and detect problems (e.g., insufficient funds) without logging in.

**Independent Test**: With a schedule due for execution, trigger execution; verify the user receives a success notification with amount, beneficiary, and execution date — independently of the schedule creation or management flows.

**Acceptance Scenarios**:

1. **Given** a scheduled transfer executes successfully, **When** the execution completes, **Then** the user receives an in-app notification stating the amount, beneficiary, and execution date within 5 minutes of execution.
2. **Given** a scheduled transfer fails (e.g., insufficient funds), **When** the failure occurs, **Then** the user receives a failure notification with the reason and a prompt to resolve the issue; the schedule moves to `EXECUTION_FAILED` state.
3. **Given** a schedule has a next execution date within 24 hours, **When** the system checks pending schedules, **Then** the user receives an advance reminder notification.
4. **Given** a user has opted out of email notifications, **When** a schedule executes, **Then** they receive only the in-app notification; no email is sent.

---

### User Story 4 - Schedule Reaches End Date and Completes (Priority: P2)

A user set up a 12-month schedule for a loan repayment. When the final scheduled transfer executes and the end date is reached, the schedule automatically completes — the user is notified, the schedule is marked `COMPLETED`, and no further transfers occur. The historical record of all executions remains accessible.

**Why this priority**: Proper lifecycle completion prevents accidental over-payment and gives users confidence that the system handles termination correctly.

**Independent Test**: With a schedule configured for exactly 2 occurrences, trigger both executions; verify the schedule moves to `COMPLETED` after the second, no third execution is attempted, and the user is notified.

**Acceptance Scenarios**:

1. **Given** a schedule's final execution date has passed and the transfer executed, **When** the system processes the completion, **Then** the schedule status becomes `COMPLETED` and no further transfers are scheduled.
2. **Given** a completed schedule, **When** a user views it in the schedule list, **Then** it is shown in a "Completed" section with the full execution history (dates, amounts, statuses).
3. **Given** a completed schedule, **When** the system's scheduling engine evaluates pending work, **Then** the completed schedule is never selected for execution.

---

### Edge Cases

- What happens when the scheduled execution date falls on a bank holiday or weekend? → The transfer executes on the next available business day; the user is informed of this adjustment at schedule creation and in the advance reminder notification.
- What happens when the source account has insufficient funds at execution time? → The transfer fails, the schedule moves to `EXECUTION_FAILED` state, the user is notified with a clear reason, and they must resolve the issue (top up account or modify the amount) before the schedule retries or they manually re-trigger.
- What happens when a user's account is closed or frozen while a schedule is active? → The execution fails, the schedule is suspended, and the user (or their account manager) is notified to take action.
- What happens if the system is unavailable at the exact scheduled execution time? → The system executes the transfer as soon as it recovers, provided the execution date is within a defined catch-up window (e.g., same business day). If the window has passed, the occurrence is skipped and marked as missed with a notification to the user.
- What happens when a schedule has only one occurrence remaining and the user modifies the end date to add more? → The system recalculates remaining occurrences from the next pending execution date and updates the schedule; the historical executions are unaffected.
- What happens when a user tries to create a duplicate schedule (same beneficiary, amount, interval as an existing active one)? → The system warns the user that a similar schedule exists and asks them to confirm before creating a potential duplicate.
- What happens if the total of all active schedule amounts would exceed a regulatory transfer limit? → The system warns the user and may require additional authorisation for the new schedule.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an authenticated user to create a recurring transfer schedule specifying: source account, beneficiary, amount, currency, interval (daily, weekly, fortnightly, monthly, quarterly, annually), start date, and end date.
- **FR-002**: System MUST validate that the start date is in the future, the end date is after the start date, and at least one execution will occur within the defined date range.
- **FR-003**: System MUST display a confirmation summary showing all calculated future execution dates before the user finalises the schedule.
- **FR-004**: System MUST enforce that the per-execution amount does not exceed the user's applicable single-transfer limit; schedules breaching this limit MUST be rejected at creation time.
- **FR-005**: System MUST support the following schedule states and transitions: `ACTIVE` → `PAUSED` → `ACTIVE`, `ACTIVE` → `CANCELLED`, `ACTIVE` → `EXECUTION_FAILED`, `ACTIVE` → `COMPLETED`, `EXECUTION_FAILED` → `ACTIVE` (after user resolution).
- **FR-006**: System MUST allow a user to pause, resume, modify (amount, end date), or cancel any of their own active schedules.
- **FR-007**: System MUST execute each scheduled transfer automatically on the correct date, or on the next available business day if the scheduled date falls on a weekend or bank holiday.
- **FR-008**: System MUST notify the user for each of the following events: schedule created, execution succeeded, execution failed, advance reminder (≥24 hours before next execution), schedule completed, schedule cancelled.
- **FR-009**: System MUST allow users to opt out of email notifications while retaining in-app notifications; notification preferences are per-user and persist across sessions.
- **FR-010**: System MUST maintain a complete, immutable execution history for each schedule, recording: execution date, amount transferred, status (succeeded/failed/skipped), and failure reason if applicable.
- **FR-011**: System MUST mark a schedule as `COMPLETED` automatically after its final scheduled execution and MUST NOT attempt any further executions.
- **FR-012**: System MUST detect and warn (but not block) when a new schedule appears to duplicate an existing active schedule (same beneficiary, amount, currency, and interval).
- **FR-013**: System MUST display all schedules belonging to the authenticated user, grouped by status (Active, Paused, Completed, Cancelled), with key summary data per schedule.
- **FR-014**: System MUST enforce a per-user limit on the number of active schedules (default: 20) and reject new schedule creation beyond this limit with a clear explanation.

### Security & Compliance Requirements *(mandatory for banking systems)*

- **SEC-001**: All schedule creation, modification, and cancellation operations MUST be authenticated; unauthenticated requests MUST be rejected before any data access.
- **SEC-002**: A user MUST only be able to view or modify their own schedules; cross-user access MUST be structurally impossible, not only filtered at the application layer.
- **SEC-003**: The scheduling engine, when executing transfers autonomously, MUST carry a verified, delegated user identity for each operation — it MUST NOT execute transfers under a generic system identity. The delegated identity MUST be validated before each execution.
- **SEC-004**: All schedule lifecycle events (create, pause, resume, modify, cancel, execute, fail, complete) MUST be logged to the audit log with the authenticated actor identity, timestamp, and before/after state.
- **SEC-005**: Schedule data containing beneficiary account details MUST be masked in notifications and list views (last 4 digits only); full account numbers MUST NOT appear outside the schedule detail view.
- **SEC-006**: The scheduling engine MUST apply the principle of least privilege: it MUST only hold permission to execute transfers for schedules that are currently `ACTIVE` and due for execution; it MUST NOT hold standing permission to modify account balances outside of scheduled executions.
- **SEC-007**: All communication between the scheduling engine and the payment execution system MUST be authenticated, authorised, and encrypted in transit.
- **SEC-008**: Schedule creation that would result in transfers exceeding applicable regulatory thresholds (e.g., AML reporting limits) MUST trigger an enhanced authorisation step or flag for compliance review.

### Data Integrity Requirements *(mandatory for financial features)*

- **DI-001**: Schedule creation, execution, and state transitions MUST be atomic: the schedule state change and the corresponding audit log entry MUST succeed or fail together; partial commits are not permitted.
- **DI-002**: Each transfer execution initiated by a schedule MUST be idempotent: if the execution system is called more than once for the same scheduled occurrence (e.g., due to a retry), only one transfer MUST be processed and settled.
- **DI-003**: Amount values in schedules MUST use precise decimal types; floating-point representations are forbidden for any monetary value.
- **DI-004**: The system MUST maintain an `audit_log` table containing at minimum: `operation_type` (controlled enum), `operation_id` (UUID), `initiator` (authenticated identity or `system/scheduler` for automated operations), `timestamp` (server-set TIMESTAMPTZ). The table MUST be append-only.
- **DI-005**: The controlled `operation_type` vocabulary for scheduled transfer operations MUST include at minimum: `SCHEDULE_CREATED`, `SCHEDULE_MODIFIED`, `SCHEDULE_PAUSED`, `SCHEDULE_RESUMED`, `SCHEDULE_CANCELLED`, `SCHEDULE_COMPLETED`, `SCHEDULE_EXECUTION_SUCCEEDED`, `SCHEDULE_EXECUTION_FAILED`, `SCHEDULE_EXECUTION_SKIPPED`.
- **DI-006**: Every state-changing operation MUST produce exactly one `audit_log` entry in the same ACID transaction. Operations that cannot write their audit entry MUST be rolled back.
- **DI-007**: The execution history for a schedule MUST be immutable once written; no UPDATE or DELETE operations on execution history records are permitted in application code.

### Performance Requirements

- **PERF-001**: Schedule creation, modification, and cancellation MUST complete and return a response to the user within 2 seconds (p95).
- **PERF-002**: The schedule list view MUST load within 500ms (p95) for a user with up to 20 active schedules.
- **PERF-003**: The scheduling engine MUST execute all due transfers within 5 minutes of their scheduled execution time under normal operating conditions.
- **PERF-004**: The system MUST support at least 10,000 active schedules across all users without degradation in execution timeliness.

### Key Entities

- **Transfer Schedule**: A user-defined recurring transfer plan. Contains: source account, beneficiary, amount, currency, interval, start date, end date, status, and notification preferences. Owned by a single authenticated user.
- **Schedule Execution**: A single instance of the schedule being triggered. Records: scheduled date, actual execution date, amount, status (succeeded/failed/skipped), failure reason, and a reference to the audit log entry. Immutable once written.
- **Schedule Status**: The governed state machine for a schedule: `ACTIVE`, `PAUSED`, `EXECUTION_FAILED`, `COMPLETED`, `CANCELLED`.
- **Interval**: The recurrence unit for a schedule. Supported values: daily, weekly, fortnightly, monthly, quarterly, annually.
- **Delegated Execution Identity**: The verified, user-scoped identity used by the scheduling engine when executing a transfer autonomously on behalf of a user. Distinct from a human-initiated session identity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a recurring transfer schedule in under 3 minutes from navigation to confirmation, for 90% of users in usability testing.
- **SC-002**: 99.9% of scheduled transfers execute within 5 minutes of their scheduled time under normal operating conditions, measured over a 30-day rolling window.
- **SC-003**: Zero incidents of a scheduled transfer executing more than once for the same occurrence (idempotency guarantee), verified by automated reconciliation checks.
- **SC-004**: Zero incidents of one user's schedule data appearing in another user's view or being modified by another user, verified by automated isolation tests on every deployment.
- **SC-005**: 95% of execution failure notifications are delivered to the user within 5 minutes of the failure event.
- **SC-006**: 100% of schedule lifecycle events produce a corresponding audit log entry, verified by daily reconciliation checks.
- **SC-007**: User task completion rate for "create a recurring schedule and verify its first execution" reaches 85% on first attempt without assistance, measured at launch.

## Assumptions

- The existing Fund Transfer Service (spec 001) provides the underlying transfer execution capability; this feature adds scheduling on top of it — it does not reimplement transfer logic.
- Bank holiday calendars for the supported jurisdictions are maintained by a separate calendar service; this feature consumes that service to determine next-business-day execution dates.
- Notification delivery (in-app, email) is handled by an existing platform notification service; this feature triggers events to that service and does not build a new notification system.
- The delegated execution identity mechanism (by which the scheduler acts on behalf of a user without their real-time presence) requires a platform-level capability. Its design is out of scope for this spec and will be addressed as an S-ADR at planning phase.
- "Monthly" interval means same day of the month (e.g., the 15th); if the month has fewer days than the scheduled day (e.g., the 31st in February), execution occurs on the last day of that month.
- The 20-active-schedule-per-user limit and the single-transfer amount limit are configurable defaults; adjustments require a governed configuration change.
- FX (foreign currency) recurring transfers are out of scope for v1; the feature supports domestic currency transfers only. FX scheduling will be addressed in a future spec building on the FX Transfer Service (spec 002).
- The scheduling engine runs within the same platform trust domain as the banking backend; it does not cross an external network boundary to execute transfers.
