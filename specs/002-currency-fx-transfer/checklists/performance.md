# Performance Requirements Checklist: Currency Conversion & Cross-Currency Transfer

**Purpose**: Validate quality, clarity, and completeness of performance requirements before submitting the spec (author self-review, lightweight)
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)
**Scope**: PERF-001 – PERF-003 (dedicated performance section)
**Audience**: Author (pre-submission self-review)
**Depth**: Lightweight sanity check

---

## Requirement Clarity

- [x] CHK001 - Is "normal load" in PERF-001 defined with measurable parameters (e.g., expected concurrent user count or request rate)? [Ambiguity, Spec §PERF-001] → Fixed: "normal load" defined as up to 500 concurrent authenticated sessions in the measurement baseline.
- [x] CHK002 - Does PERF-001 clarify whether the 500ms budget covers server-side processing only or end-to-end response time (including network latency)? [Ambiguity, Spec §PERF-001] → Fixed: measurement baseline specifies "server-side processing time measured at the service boundary (excluding client-side rendering and network transit)".
- [x] CHK003 - Does PERF-002 specify whether the 2-second SLA applies separately to initiation and confirmation steps, or as a combined per-operation budget? [Ambiguity, Spec §PERF-002] → Fixed: PERF-002 now states "each individually complete in under 2 seconds".
- [x] CHK004 - Is "performance degradation" in PERF-003 quantified with measurable thresholds (e.g., ≤X% increase in p95 latency at 500 concurrent sessions vs. baseline)? [Ambiguity, Spec §PERF-003] → Fixed: PERF-003 now states p95 MUST NOT exceed 150% of baseline targets (≤750ms read, ≤3s write) at peak load.
- [x] CHK005 - Is "concurrent transfer session" in PERF-003 defined (e.g., in-flight transaction, active HTTP connection, or authenticated user session)? [Ambiguity, Spec §PERF-003] → Fixed: defined as "an authenticated user session with at least one transfer in PENDING or PROCESSING state".

## Requirement Completeness

- [x] CHK006 - Are throughput requirements (e.g., transfers per second) documented for PERF-002 write operations? [Gap, Spec §PERF-002] → Fixed: PERF-002 now requires ≥50 combined transfer operations per second.
- [x] CHK007 - Are error-rate thresholds defined alongside latency targets for performance conditions? [Gap] → Fixed: PERF-001 adds ≤0.1% error rate; PERF-002 adds ≤0.5% error rate under normal load.
- [x] CHK008 - Are degradation requirements or graceful-degradation expectations defined for load exceeding the 500-session threshold in PERF-003? [Gap, Spec §PERF-003] → Fixed: PERF-003 now requires explicit capacity error rejection for >500 sessions (no unbounded latency growth).
- [x] CHK009 - Are performance requirements defined for the exchange rate refresh operation (FR-003), which runs on a configurable interval and could contend with user-facing operations? [Gap] → Fixed: new PERF-004 added (≤10s p95 for refresh, must not block user-facing operations).

## Acceptance Criteria Quality

- [x] CHK010 - Can PERF-001's 500ms p95 target be objectively measured without ambiguity — is the measurement point (client, load balancer, or service boundary) specified? [Measurability, Spec §PERF-001] → Fixed: measurement baseline specifies "service boundary".
- [x] CHK011 - Are load-test criteria specified to validate PERF-003 (e.g., test tool, scenario definition, duration, and pass/fail threshold)? [Gap, Spec §PERF-003] → Fixed: new PERF-006 added (500 concurrent sessions × 10 minutes sustained; deployment blocked unless targets validated).
- [x] CHK012 - Is the p95 measurement methodology defined (e.g., measurement window duration and target environment — dev, staging, production-equivalent)? [Clarity, Gap] → Fixed: measurement baseline specifies "5-minute rolling window in a staging environment sized equivalently to production".

## Consistency

- [x] CHK013 - Are PERF-001 (500ms read) and PERF-002 (2s write) thresholds explicitly aligned with the constitution's Principle VI performance standards to avoid silent divergence? [Consistency, Spec §PERF-001, §PERF-002] → Fixed: measurement baseline now explicitly states alignment with constitution Principle VI.
- [x] CHK014 - Are PERF-001 (500ms API) and SC-001 (3-second full page load including fresh rates) requirements reconcilable — does SC-001 account for overhead beyond the API call itself? [Consistency, Spec §SC-001, §PERF-001] → Fixed: SC-001 updated to clarify 3-second is end-to-end (user-perceived) encompassing PERF-001 server-side budget plus network and rendering; explicitly stated as compatible.

## Edge Case Coverage

- [x] CHK015 - Are performance expectations defined for degraded-mode operation (e.g., stale-rate read-only display, circuit breaker open for the FX provider)? [Gap, Edge Case] → Fixed: PERF-004 requires cached rates remain available during refresh; PERF-005 requires stale-rate fallback within 5s timeout.
- [x] CHK016 - Is the acceptable latency (or timeout behavior) specified when the external FX rate provider is slow or unresponsive, to bound the impact on PERF-001 and PERF-002? [Gap, Edge Case] → Fixed: new PERF-005 added (5-second client-side timeout; must not propagate provider latency to user-facing operations).

---

## Second Run — New Additions (PERF-004–006 + Measurement Baseline)

**Added**: 2026-06-16 | **Scope**: PERF-004, PERF-005, PERF-006, measurement baseline paragraph | **Depth**: Lightweight | **Audience**: Author self-review

### Requirement Clarity

- [x] CHK017 - Does the measurement baseline (5-minute rolling window, service boundary, production-equivalent staging) explicitly apply to PERF-004 and PERF-005, or is it silently scoped to PERF-001–003 only? [Consistency, Spec §PERF-004, §PERF-005] → Fixed: measurement baseline now explicitly states it applies to PERF-001 through PERF-004; PERF-005 is clarified as a timeout constraint not subject to the rolling-window measurement.
- [x] CHK018 - Does PERF-004 specify the precise start and end points of the 10-second (p95) window — e.g., from the moment the refresh is triggered to the moment all updated rates are available for read? [Clarity, Spec §PERF-004] → Fixed: PERF-004 now states "measured from the moment the refresh is triggered (scheduled timer fires or on-demand request arrives at the service) to the moment updated rates are committed to the DB snapshot and available for read-serving."
- [x] CHK019 - Is the 5-second FX provider timeout in PERF-005 defined as a per-request (per-call) timeout, and is it configurable by operations or hardcoded? [Clarity, Spec §PERF-005] → Fixed: PERF-005 now specifies "per-request client-side timeout of 5 seconds (configurable via the FX_PROVIDER_TIMEOUT_SECONDS environment variable)."
- [x] CHK020 - Does PERF-005 define any latency expectation for the fallback path itself — i.e., is "immediately serve cached rates" bound by any measurable SLA, or is "immediately" left undefined? [Ambiguity, Spec §PERF-005] → Fixed: PERF-005 now requires the fallback path complete "within the PERF-001 latency budget (≤500ms p95 at the service boundary)"; "immediately" removed.

### Requirement Completeness

- [x] CHK021 - Is an error-rate threshold defined for PERF-004 refresh operations, consistent with the approach used in PERF-001 (≤0.1%) and PERF-002 (≤0.5%)? [Gap, Consistency, Spec §PERF-004] → Fixed: PERF-004 now requires "The error rate for refresh operations MUST NOT exceed 1% under normal load."
- [x] CHK022 - Does PERF-005 specify whether the system should retry the FX provider call before falling back to cached rates, and if so, how many retries and with what timing? [Gap, Spec §PERF-005] → Fixed: PERF-005 now specifies "retry the provider up to 2 times with exponential backoff (initial delay: 500ms, factor: 2×)" before falling back.
- [x] CHK023 - Does PERF-006 specify a ramp-up period for reaching 500 concurrent sessions (e.g., gradual ramp vs. instant spike), which determines whether the test reflects realistic or worst-case conditions? [Gap, Spec §PERF-006] → Fixed: PERF-006 now specifies "preceded by a 2-minute linear ramp-up from 0 to 500 concurrent sessions."
- [x] CHK024 - Is "production-equivalent staging environment" in PERF-006 defined with specific, verifiable resource criteria (e.g., compute capacity ratio, database record volume, network configuration) so it can be objectively confirmed? [Ambiguity, Spec §PERF-006] → Fixed: PERF-006 now lists three verifiable criteria: same CPU/memory tier, ≥10,000 representative DB records, and network latency within 10% of production baseline.

### Acceptance Criteria Quality

- [x] CHK025 - Does PERF-006 define measurable pass/fail criteria for the graceful-degradation behaviour at peak load — e.g., is the capacity-error rejection requirement (from PERF-003) included as an explicit load-test pass criterion? [Measurability, Spec §PERF-006, §PERF-003] → Fixed: PERF-006 now explicitly includes "verification that new transfer initiations beyond 500 concurrent sessions are rejected with an HTTP 503 capacity error" as a named pass criterion.
- [x] CHK026 - Is the enforcement mechanism for the PERF-006 deployment gate specified (automated CI/CD gate vs. manual sign-off), so it is objectively verifiable as an enforceable requirement? [Clarity, Gap, Spec §PERF-006] → Fixed: PERF-006 now specifies "This gate MUST be enforced by an automated CI/CD pipeline step that parses load test results and fails the pipeline if any criterion is not met; manual override requires written approval from the technical lead with documented justification."

### Edge Case Coverage

- [x] CHK027 - Are performance requirements defined for the scenario where a scheduled refresh and an on-demand refresh are triggered concurrently — does the spec address whether they serialise, deduplicate, or run in parallel? [Coverage, Edge Case, Spec §PERF-004] → Fixed: PERF-004 now requires "If a scheduled refresh and an on-demand refresh are triggered concurrently, they MUST be deduplicated into a single in-flight refresh operation; only one provider call MUST be made."

---

## Notes

- Check items off as completed: `[x]`
- Add findings or comments inline after each item
- `[Gap]` = requirement is missing; `[Ambiguity]` = requirement exists but is unclear
- Items are numbered sequentially for easy cross-reference
