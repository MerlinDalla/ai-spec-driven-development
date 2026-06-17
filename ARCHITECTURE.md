# Architecture Overview — Spec-Kit Workflows

Complete system architecture for AI-powered spec-kit exercises and production workflows.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Actions Orchestrator                 │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Exercise 1: Simple Pipeline (speckit-workflow.yml)       │   │
│  │ • Input: Feature description                             │   │
│  │ • Output: spec.md, plan.md, tasks.md                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Exercise 2: Enterprise Pipeline (exercise-2-*.yml)       │   │
│  │ • Phase 1: Spec + Fan-out reviews (security, edge-cases) │   │
│  │ • Phase 2: Plan + Cross-check validation                 │   │
│  │ • Phase 3: Tasks + Implement + Audit + Remediate        │   │
│  │ • Agents: qa-advisor (reviewer), developer (fixer)      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Exercise 3: Multi-Service Orchestration                  │   │
│  │ • Parallel service specs, plans, implementation           │   │
│  │ • Cross-service compatibility validation                 │   │
│  │ • Integrated testing                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Dependency Management Workflow (dependency-*.yml)         │   │
│  │ • CVE scanning (Python, Node.js, .NET)                   │   │
│  │ • Outdated package detection                             │   │
│  │ • License compliance checking                            │   │
│  │ • Automated issue creation                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Release & Deployment Workflow (release-*.yml)            │   │
│  │ • Version validation & tagging                           │   │
│  │ • Build & package                                        │   │
│  │ • GitHub release creation                                │   │
│  │ • Blue-green deployment (staging/production)            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         ↓                                            ↓
┌─────────────────────────────────────────────────────────────────┐
│             GitHub Copilot Integration Layer                     │
│                                                                   │
│  • specify CLI (npm package, version 0.9.5)                     │
│  • GH_TOKEN authentication                                      │
│  • SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS="--allow-all-tools"  │
│  • Headless mode for CI/CD                                      │
└─────────────────────────────────────────────────────────────────┘
         ↓                                            ↓
┌──────────────────────────────────────────────────────────────────┐
│                    Agent Ecosystem                                │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ qa-advisor Agent (.github/agents/qa-advisor.agent.md)     │  │
│  │ • Role: Reviewer (security + edge-case analysis)          │  │
│  │ • Runs: Phase 1, parallel with other reviewers            │  │
│  │ • Outputs: review-security.md, review-edge-cases.md      │  │
│  │ • Gate Decision: APPROVED / NEEDS REVISION / CONDITIONAL   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ developer Agent (.github/agents/developer.agent.md)        │  │
│  │ • Role: Implementer (code writer + bug fixer)             │  │
│  │ • Runs: Phase 3 (implementation + remediation loop)       │  │
│  │ • Outputs: Source code, tests, migrations                 │  │
│  │ • Feedback Loop: Reviewer ↔ Developer ↔ Reviewer          │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
         ↓                                            ↓
┌──────────────────────────────────────────────────────────────────┐
│               Artifact & Configuration Storage                    │
│                                                                    │
│  .specify/ (local workflow configuration)                        │
│  ├── workflows/speckit/workflow.yml (main definition)            │
│  ├── memory/ (agent state & context)                             │
│  ├── templates/ (artifact templates)                             │
│  └── scripts/ (helper scripts)                                   │
│                                                                    │
│  .github/agents/ (custom agent definitions)                      │
│  ├── qa-advisor.agent.md                                         │
│  └── developer.agent.md                                          │
│                                                                    │
│  specs/ (generated artifacts per feature)                        │
│  ├── 001-feature-name/                                           │
│  │   ├── spec.md                                                 │
│  │   ├── plan.md                                                 │
│  │   ├── tasks.md                                                │
│  │   ├── review-security.md                                      │
│  │   ├── review-edge-cases.md                                    │
│  │   ├── data-model.md                                           │
│  │   ├── contracts/                                              │
│  │   └── checklists/                                             │
│  └── 002-another-feature/                                        │
│      └── ...                                                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow

### Exercise 1: Linear Pipeline

```
Input
  ↓
(specify: Copilot generates spec.md)
  ↓
Spec Artifacts
  ├── spec.md (requirements)
  ├── data-model.md (schema)
  └── contracts/api.yaml
  ↓
(Gate 1: Review Spec)
  ↓
(specify: Copilot generates plan.md)
  ↓
Plan Artifacts
  ├── plan.md (strategy)
  ├── architecture.md
  └── timeline.md
  ↓
(Gate 2: Review Plan)
  ↓
(specify: Copilot generates tasks.md)
  ↓
Final Artifacts
  ├── tasks.md (breakdown)
  ├── test-plan.md
  └── acceptance-criteria.md
  ↓
Output (Download Artifacts)
```

### Exercise 2: Multi-Phase with Reviews & Audits

```
Input: Feature Description
  ↓
PHASE 1: SPEC + FAN-OUT REVIEWS
  ├── (specify: Generate spec.md)
  │    ↓
  │   spec.md (base)
  ├── PARALLEL REVIEWS:
  │   ├── (qa-advisor: Security Review)
  │   │    → review-security.md
  │   └── (qa-advisor: Edge Cases Review)
  │        → review-edge-cases.md
  ├── (specify: Incorporate feedback, respecify)
  │    ↓
  │   spec.md (revised)
  └── (Gate 1: review-spec → APPROVED)
      ↓
PHASE 2: PLAN + VALIDATION
  ├── (specify: Generate plan.md from spec)
  │    ↓
  │   plan.md
  ├── (analyze: Cross-check spec ↔ plan)
  │    → Verify requirement coverage
  │    → Check for consistency
  │    → Estimate task breakdown
  └── (Gate 2: review-plan → APPROVED)
      ↓
PHASE 3: IMPLEMENTATION + AUDIT + REMEDIATION
  ├── (specify: Generate tasks.md)
  ├── (developer: Implement features)
  │    → Write code
  │    → Write tests
  │    → Run linting
  ├── (NuGet MCP: Dependency audit)
  │    → Scan for CVEs
  │    → Identify vulnerabilities
  │    → Generate report
  └── REMEDIATION LOOP:
      ├── (qa-advisor: Identify issues)
      ├── (developer: Apply fixes)
      ├── (qa-advisor: Verify fixes)
      └── Repeat until resolved
      ↓
  └── (Gate 3: sign-off → MERGE)
      ↓
Output (All Artifacts + Audit Report)
```

---

## 🔄 Agent Communication

### Bidirectional Feedback Loop

```
        ┌─────────────────┐
        │   Code Review   │
        │  (qa-advisor)   │
        └────────┬────────┘
                 │
         "Issues found:"
        ├── Missing validation
        ├── No rate limiting
        └── TODO in code
                 │
                 ↓
        ┌─────────────────┐
        │  Code Fixes     │
        │  (developer)    │
        └────────┬────────┘
                 │
         "Fixes applied:"
        ├── Added validation
        ├── Rate limiting
        └── Resolved TODOs
                 │
                 ↓
        ┌─────────────────┐
        │  Verification   │
        │  (qa-advisor)   │
        └────────┬────────┘
                 │
        ✅ All issues resolved
        Ready for merge
```

---

## 🔐 Security & Authentication

### Token Flow

```
User Creates GH_TOKEN Secret
         ↓
   GitHub Repository
         ↓
   GitHub Actions Runner
         ↓
   ${{ secrets.GH_TOKEN }}
         ↓
   Environment Variable
   ├── GH_TOKEN (for Copilot)
   ├── GITHUB_TOKEN (for artifacts)
   └── SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS
         ↓
   specify CLI
   ├── Authenticates to GitHub
   ├── Calls Copilot API
   └── Generates artifacts
```

---

## 📦 Dependency Graph

### Project Dependencies

```
Fund Transfer Service
├── Python 3.12 Runtime
│   ├── FastAPI 0.104+
│   ├── SQLAlchemy 2.0+ (async)
│   ├── asyncpg (PostgreSQL driver)
│   ├── Pydantic 2.0+
│   ├── pytest (testing)
│   ├── ruff (linting)
│   └── mypy (type checking)
│
├── PostgreSQL 16 Database
│   ├── Data models
│   ├── Migrations (Alembic)
│   └── Transactions
│
├── GitHub Copilot Integration
│   ├── specify CLI (npm package)
│   ├── gh CLI (GitHub command line)
│   ├── Node.js 20+
│   └── GH_TOKEN authentication
│
└── GitHub Actions Infrastructure
    ├── Artifact storage
    ├── Secret management
    ├── Workflow orchestration
    └── Environment variables
```

---

## 🎯 Workflow Decision Tree

```
Feature Request Received
        ↓
    ┌───────────────────┐
    │ Complexity Level? │
    └────┬──────────────┘
         │
    ┌────┴─────────────────────┐
    ↓                           ↓
Simple Feature          Complex/Secure Feature
    │                           │
    └─→ Exercise 1              └─→ Exercise 2
        (Basic Pipeline)            (Enterprise Pipeline)
        ├── Spec                    ├── Spec + Reviews
        ├── Plan                    ├── Plan + Validation
        └── Tasks                   ├── Implementation
                                    ├── Audit
                                    └── Remediation
    ↓                           ↓
Ready for Implementation   Production-Ready Code
    │                           │
    └─→ Merge to Main ←─────────┘
        ├── Run Tests
        ├── Deploy Staging
        └── Deploy Production (via Release Workflow)
```

---

## 📈 Scaling Strategy

### Single Service (Current)
- Exercise 1 & 2 handle feature generation for fund_transfer service
- Dependency management scans all packages
- Release workflow deploys to staging/production

### Multiple Services (Exercise 3)
```
Services:
├── fund_transfer (core API)
├── notifications (email/SMS)
├── fx_rates (exchange rates)
└── reporting (analytics)

Exercise 3 Workflow:
1. Generate specs for each service in parallel
2. Validate cross-service compatibility
3. Generate plans for each service
4. Coordinate implementation with dependency awareness
5. Run integrated tests
6. Deploy all services atomically
```

### Multi-Team Organization
```
Team 1: Fund Transfer Team
├── Exercise 2 Workflow (custom features)
├── Dependency Management (security)
└── Release Workflow (deploy)

Team 2: Platform Team
├── Exercise 3 Workflow (orchestration)
├── Infrastructure (provisioning)
└── Monitoring (observability)

Central: Governance
├── Agent Configuration
├── Security Policies
└── Deployment Gates
```

---

## ⚙️ Configuration Files

### Key Files

| File | Purpose | Key Settings |
|------|---------|--------------|
| `.specify/workflows/speckit/workflow.yml` | Main workflow definition | Phases, gates, agents |
| `.github/workflows/speckit-workflow.yml` | Exercise 1 implementation | GitHub Actions triggers |
| `.github/workflows/exercise-2-*.yml` | Exercise 2 implementation | Multi-phase pipeline |
| `.github/agents/qa-advisor.agent.md` | Security reviewer | Threat modeling rules |
| `.github/agents/developer.agent.md` | Code implementer | Language, frameworks, testing |
| `.github/secrets` | Authentication | GH_TOKEN, API keys |
| `.env.local` | Local development | Environment variables |

---

## 🧪 Testing Strategy

### Unit Tests (Developer)
```
src/fund_transfer/
├── models/ → test_models.py
├── services/ → test_services.py
├── api/ → test_api_routes.py
└── repositories/ → test_repositories.py
```

### Integration Tests (CI/CD)
```
tests/integration/
├── test_database_integration.py
├── test_api_integration.py
├── test_service_integration.py
└── test_end_to_end.py
```

### Security Tests (Dependency Management)
```
CVE Scanning:
├── Python: safety check
├── Node.js: npm audit
└── .NET: dotnet package audit

License Compliance:
├── pip-licenses
└── npm-check-licenses
```

---

## 📊 Metrics & Monitoring

### Workflow Metrics
- Spec generation time: < 5 minutes
- Review time: < 10 minutes
- Plan generation time: < 5 minutes
- Implementation time: < 30 minutes
- Total pipeline time: < 60 minutes

### Code Quality Metrics
- Test coverage: > 80%
- Linting score: 100% passing
- Type coverage: > 95%
- Security scan: 0 critical issues
- CVE vulnerabilities: 0 known vulnerabilities

### Performance Metrics
- API response time: < 500ms
- Database query time: < 100ms
- Throughput: > 1000 requests/second
- Error rate: < 0.1%

---

## 🚀 Future Enhancements

### Phase 4 (Planned)
- [ ] Knowledge base integration (Docs)
- [ ] ML-based issue detection
- [ ] Automated root cause analysis
- [ ] Predictive performance modeling

### Phase 5 (Planned)
- [ ] Multi-repo orchestration framework
- [ ] Team charter system
- [ ] Role-based access control (RBAC)
- [ ] Audit logging & compliance reporting

### Phase 6 (Vision)
- [ ] Self-healing infrastructure
- [ ] Autonomous deployment optimization
- [ ] Cross-org knowledge sharing
- [ ] Industry best practices catalog

---

## 📚 Related Documentation

- **README.md** — User-facing overview and quick start
- **SETUP.md** — Detailed setup instructions for all environments
- **.github/agents/qa-advisor.agent.md** — Security reviewer capabilities
- **.github/agents/developer.agent.md** — Implementation patterns and guidelines
- **public/07-workflow/workflows-with-human-gates__clear.md** — Training materials

---

**Last Updated:** June 17, 2026  
**Architecture Version:** 1.0  
**Status:** Production Ready ✅
