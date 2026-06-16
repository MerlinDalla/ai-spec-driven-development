<!--
Sync Impact Report:
- Version: 1.1.0 → 1.2.0 (MINOR — new Principle VIII added: Secure Architecture Governance,
  sourced from the architecture-governance preset constitution-addendum)
- Modified Principles: None (existing principles unchanged)
- Added Sections:
    VIII. Secure Architecture Governance — architectural security principles, STRIDE/CAPEC
    threat modeling, arc42/S-ADR documentation standards, Zero Trust & OWASP SAMM,
    memory-safe language guidance, and evidence location conventions
- Removed Sections: None
- Templates Updated:
  ✅ .specify/memory/constitution.md — Principle VIII added (this file)
  ✅ .specify/templates/plan-template.md — Constitution Check expanded with
     "Secure Architecture Governance" gate items
  ⚠ .specify/templates/spec-template.md — No structural change required;
     spec-addendum from preset injects architecture items per-spec at plan time
  ⚠ .specify/templates/tasks-template.md — No structural change required;
     tasks-addendum from preset injects S-ADR and threat-model tasks at task-gen time
- Carried-forward TODOs:
  ⚠ TODO(AUDIT_FIELD_NAMING): The existing Fund Transfer Service audit_log table uses
    field names that differ from the canonical names mandated here:
      canonical operation_id → current field name: id (UUID PK)
      canonical initiator    → current field name: actor_identity
    A migration and code refactor should align the existing schema to this standard.
- Evidence directory: docs/security/ (S-ADRs → docs/security/adr/) — to be created
  when first security artifact is produced.
-->

# AI Spec Driven Constitution

## Core Principles

### I. Security-First & Compliance (NON-NEGOTIABLE)

All code MUST adhere to banking security standards and regulatory requirements:
- Authentication and authorization MUST be implemented on all endpoints
- Sensitive data (PII, financial data, credentials) MUST be encrypted at rest and in transit
- All security-sensitive operations MUST be logged with audit trails
- OWASP Top 10 vulnerabilities MUST be prevented by design
- Code MUST pass security scanning before deployment
- Secrets MUST NOT be committed to version control; use secure vault services

**Rationale**: Banking systems handle sensitive financial data and must comply with regulatory
standards (PCI-DSS, GDPR, SOC 2). Security breaches can result in financial loss, legal
liability, and reputational damage.

### II. Data Integrity & Auditability

Financial data integrity is paramount:
- All financial transactions MUST be atomic, consistent, isolated, and durable (ACID)
- Database operations affecting financial data MUST use transactions with rollback capability
- Every state change MUST be auditable with: who, what, when, why
- Financial calculations MUST use precise decimal types (never floating point)
- Data validation MUST occur at API boundaries and before persistence
- Immutable audit logs MUST capture all financial operations

#### Audit Table Standard (NON-NEGOTIABLE)

Every system MUST maintain a dedicated `audit_log` table. This is not optional and cannot
be deferred or replaced by application-level logging alone.

**Mandatory minimum schema** — the table MUST contain at least these four columns:

| Column | Type | Rules |
|---|---|---|
| `operation_type` | controlled enum/string | MUST be drawn from a pre-defined vocabulary; free-form strings are NOT permitted |
| `operation_id` | UUID, globally unique | System-generated for each logged operation; used as the stable identifier for the audit entry |
| `initiator` | string (non-empty) | MUST reference the authenticated identity that triggered the action (e.g., JWT `sub` claim); MUST be `system` for automated/background operations |
| `timestamp` | TIMESTAMPTZ, server-set | MUST be set by the database server (not the application); immutable after insert |

Additional columns (e.g., `affected_entities`, `amount`, `outcome`, `detail`, `request_id`)
are permitted and encouraged but do not replace the four mandatory columns above.

**Universal action coverage rule**: Every state-changing operation in the system — including
but not limited to: record creation, update, deletion, fund transfer, status transition, and
configuration change — MUST produce exactly one `audit_log` entry. Read-only operations
(queries, health checks) are exempt.

**Enforcement rules**:
- Audit entries MUST be written in the same ACID transaction as the operation they record;
  an operation that cannot write its audit entry MUST be rolled back entirely.
- The audit table MUST be append-only: UPDATE and DELETE operations on `audit_log` are
  forbidden in application code and MUST be blocked at the database level where possible.
- `operation_type` values MUST be defined in a shared enum or controlled vocabulary document
  before implementation; adding new values requires a documented schema change.
- Audit entries MUST NOT expose secrets, plaintext PII beyond what is required for
  traceability, or internal stack traces.

**Rationale**: A mandatory, schema-enforced audit table with a controlled operation_type
vocabulary ensures that audit coverage is complete, queryable, and consistent across all
features. Ad-hoc logging cannot guarantee completeness or support regulatory queries.

**Rationale**: Financial data errors can have severe consequences. Audit trails are required
for regulatory compliance, fraud detection, and dispute resolution.

### III. API-Driven Design

Backend services MUST expose well-defined, versioned APIs:
- RESTful or gRPC APIs MUST follow consistent design patterns
- All endpoints MUST have OpenAPI/Swagger documentation
- API contracts MUST be versioned (semantic versioning)
- Breaking changes MUST trigger major version increments
- Backward compatibility MUST be maintained for one major version
- Request/response schemas MUST be validated against contracts

**Rationale**: Clear API contracts enable frontend teams, third-party integrations, and
microservices to work independently. Versioning prevents breaking existing clients.

### IV. Test-First Development (NON-NEGOTIABLE)

TDD is mandatory for all banking functionality:
- Tests MUST be written before implementation code
- Tests MUST fail initially, then pass after implementation
- Financial calculations MUST have comprehensive unit test coverage (>95%)
- Integration tests MUST verify end-to-end transaction flows
- Contract tests MUST validate API behavior matches documentation
- All tests MUST pass before code review approval

**Rationale**: Financial software errors can cause monetary loss. Test-first development
catches bugs early and ensures requirements are clearly understood before implementation.

### V. Resilience & Error Handling

Systems MUST handle failures gracefully:
- All external service calls MUST implement timeouts, retries with exponential backoff
- Circuit breakers MUST prevent cascade failures
- Errors MUST be categorized: transient (retryable) vs permanent (non-retryable)
- User-facing errors MUST be meaningful; internal errors logged with full context
- Critical paths (payments, transfers) MUST have fallback mechanisms
- Idempotency MUST be guaranteed for financial operations

**Rationale**: Banking systems operate in distributed environments where failures are
inevitable. Proper error handling prevents data corruption and ensures business continuity.

### VI. Performance & Scalability

Systems MUST meet banking performance standards:
- API response times MUST be <500ms (p95) for read operations
- API response times MUST be <2s (p95) for write operations
- Database queries MUST be optimized with proper indexing
- Batch operations MUST support pagination and streaming for large datasets
- Resource usage (CPU, memory, connections) MUST be monitored and bounded
- Load testing MUST validate system behavior under peak conditions

**Rationale**: Banking systems must handle high transaction volumes while maintaining
responsiveness. Poor performance impacts user experience and operational efficiency.

### VII. Observability & Monitoring

All systems MUST be observable in production:
- Structured logging MUST be used (JSON format preferred)
- Critical operations MUST emit metrics (latency, error rate, throughput)
- Distributed tracing MUST be enabled for cross-service calls
- Alerts MUST be configured for SLA violations and anomalies
- Logs MUST include correlation IDs for request tracking
- Performance profiling MUST be available for troubleshooting

**Rationale**: Banking systems require 24/7 availability. Observability enables rapid
incident detection, root cause analysis, and proactive issue prevention.

### VIII. Secure Architecture Governance

Secure code without secure architecture is not sufficient. AI-generated and
human-written architecture MUST follow these principles together:

#### Architectural Security Principles

- **Trust boundaries**: Define explicit trust boundaries; validate and sanitise
  every input crossing one.
- **Defense in depth**: At least two independent security layers MUST protect
  every critical asset.
- **Least privilege**: Every component, service, and process MUST operate with
  the minimum permissions it requires.
- **Fail-safe defaults**: Deny by default, grant explicitly; error paths MUST
  fall back into a safe state.
- **Attack surface reduction**: Unused endpoints, services, and debug features
  MUST be disabled or removed before release.
- **Separation of concerns**: Authentication, authorisation, logging, and input
  validation MUST be implemented as cross-cutting concerns — never scattered
  ad hoc across features.
- **Secure configuration**: Secrets MUST be stored in platform-appropriate
  secret stores (e.g., Azure Key Vault, AWS Secrets Manager). They MUST NOT
  appear in source code or Git-tracked configuration files.
- **Supply-chain security**: Dependencies MUST come from verified registries;
  lock files MUST be committed; known-vulnerable dependencies MUST be replaced
  before release.

#### Threat Modeling and Risk

- Threat modeling MUST use `STRIDE` (Spoofing, Tampering, Repudiation,
  Information Disclosure, Denial of Service, Elevation of Privilege) as the
  base framework.
- Threats MUST be mapped against the `CIA` triad (Confidentiality, Integrity,
  Availability) for impact classification.
- For the highest-risk attack paths, relevant `CAPEC` patterns MUST be
  referenced.
- Each identified threat MUST have an explicit mitigation, an accepted-risk
  rationale, or a deferral with a defined re-evaluation trigger.

#### Architecture Documentation

- Architecturally significant security decisions MUST be captured as
  `Security Architecture Decision Records` (S-ADRs) using `adr-template`.
- Each feature or service SHOULD maintain an `arc42` Section 8 security
  cross-cutting concepts document (using `arc42-security-template`), covering:
  authentication, authorisation, encryption in transit and at rest, input
  validation, error handling, logging, dependencies, and deployment security.
- Long-lived projects SHOULD record security quality attribute scenarios using
  the `iSAQB CPSA-F` quality scenario method (`security-quality-scenarios-template`).

#### Zero Trust and OWASP SAMM

- `Zero Trust` (NIST SP 800-207) applicability MUST be explicitly evaluated
  for distributed, service-based, cloud-near, or remotely managed systems.
- Long-lived projects and workspaces SHOULD use `OWASP SAMM` to inform
  improvement plans across Governance, Design, Implementation, Verification,
  and Operations.

#### Memory-Safe Language Consideration

- When platform or runtime choices are involved, memory-safe language (MSL)
  feasibility MUST be treated as an architectural constraint. Any non-MSL
  architectural choice MUST be recorded with its rationale in an S-ADR.

#### Evidence Locations

- Architecture security evidence defaults to `docs/security/`.
- S-ADRs default to `docs/security/adr/` — one file per decision.
- Threat models, arc42 security concepts, Zero Trust assessments, OWASP SAMM
  assessments, and security quality scenarios live in `docs/security/`.

**Rationale**: Banking systems are high-value targets. Code-level security
controls are necessary but insufficient without a governed architectural
security posture. Explicit trust boundaries, documented threat models, and
S-ADRs ensure security decisions are intentional, traceable, and reviewable
— not emergent or accidental.

## Compliance & Regulatory Requirements

All features MUST comply with applicable regulations:
- **PCI-DSS**: Payment card data handling standards
- **GDPR**: Data privacy and user consent requirements
- **SOC 2**: Security controls and audit requirements
- **AML/KYC**: Anti-money laundering and identity verification
- **Data Residency**: Data storage location restrictions by jurisdiction
- **Right to be Forgotten**: User data deletion capabilities

Documentation MUST include:
- Compliance checklist for each feature
- Data classification and handling procedures
- Privacy impact assessments for personal data processing

## Quality Gates & Review Process

All code MUST pass the following gates before deployment:

**Pre-Commit**:
- Linting and formatting checks pass
- Unit tests pass locally

**Pull Request**:
- All automated tests pass (unit, integration, contract)
- Code coverage meets minimum threshold (>80%)
- Security scanning passes (no high/critical vulnerabilities)
- Peer review approved by at least one senior engineer
- API documentation updated if endpoints changed

**Pre-Deployment**:
- Load/performance tests pass
- Security audit completed for security-sensitive changes
- Rollback plan documented
- Monitoring and alerts configured

**Post-Deployment**:
- Smoke tests verify core functionality
- Metrics monitored for anomalies (first 24 hours)
- Incident response team notified of high-risk deployments

## Governance

This constitution supersedes all other development practices and guidelines.

**Amendment Process**:
- Proposed changes MUST be documented with rationale
- Changes require approval from technical lead and security officer
- MAJOR version increment for backward-incompatible changes
- MINOR version increment for new principles or expanded guidance
- PATCH version increment for clarifications only
- All affected teams MUST be notified of constitution changes

**Compliance Enforcement**:
- All pull requests MUST verify compliance with applicable principles
- Code reviewers MUST validate constitution adherence
- Non-compliance MUST be documented with mitigation plan
- Repeated violations trigger mandatory training

**Exceptions**:
- Exceptions MUST be approved by technical lead
- All exceptions MUST be documented with justification and risk assessment
- Temporary exceptions MUST have remediation timeline

**Version**: 1.2.0 | **Ratified**: 2026-06-15 | **Last Amended**: 2026-06-16
