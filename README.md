# Spec-Kit Workflow Exercises — Fund Transfer Service

Production-ready spec-kit exercises demonstrating AI-powered specification, planning, and implementation workflows using GitHub Copilot and automated agents.

## 📋 Quick Start

### Prerequisites
- GitHub account with Copilot (free trial or paid)
- Repository with GH_TOKEN secret configured
- Node.js 20+ (for specify CLI)
- Python 3.12 (for local development)

### 1. Exercise 1: Built-in Spec-Kit Pipeline
Simple, guided pipeline for feature specification.

**Step 1:** Go to **Actions** tab → **Exercise 1 · Built-in Spec-Kit Pipeline**

**Step 2:** Click **Run workflow** and enter a feature description:
```
A customer can create a recurring scheduled transfer that repeats 
daily, weekly, or monthly, with automatic processing at specified times
```

**Step 3:** Watch the pipeline:
- ✅ **Phase 1:** Generates `spec.md` (requirements)
- ✅ **Phase 2:** Generates `plan.md` (implementation strategy)
- ✅ **Phase 3:** Generates `tasks.md` (work breakdown)

**Step 4:** Download artifacts from **Artifacts** section

**Result:** Complete specification with design artifacts ✨

---

### 2. Exercise 2: Enterprise Pipeline with Reviews & Audits
Advanced multi-phase pipeline with security reviews, dependency audits, and remediation loop.

**Step 1:** Go to **Actions** tab → **Exercise 2 · Custom Workflow with Fan-Out, MCP, and Remediation Loop**

**Step 2:** Click **Run workflow** with security-focused feature:
```
Users can set spending limits on their account with daily/weekly/monthly 
caps, and the system prevents transactions that exceed these limits
```

**Step 3:** Pipeline executes 3 phases:

**Phase 1 — Spec with Fan-Out Reviews**
- Generates base `spec.md`
- **Parallel reviews:**
  - 🔍 Security & Data Protection Review (qa-advisor)
  - 🔍 Edge Cases & Failure Modes (qa-advisor)
- Gate 1: Review Specification
- Generates respecified `spec.md` with feedback incorporated

**Phase 2 — Plan & Cross-Check**
- Generates `plan.md` from approved spec
- Cross-checks spec ↔️ plan consistency
- Validates requirements coverage
- Gate 2: Review Implementation Plan

**Phase 3 — Implementation, Audit & Remediation**
- Generates `tasks.md` from plan
- Implements features (👨‍💻 developer agent)
- **Step 9:** Dependency Audit (NuGet MCP)
  - Scans .NET/Python/Node.js dependencies
  - Identifies CVE vulnerabilities
  - Reports findings
- **Step 10:** Remediation Loop
  - 🔍 Reviewer identifies issues (TODO/FIXME)
  - 👨‍💻 Developer applies fixes
  - 🔍 Reviewer verifies fixes ✅
- Gate 3: Final Sign-Off & Merge

**Result:** Production-ready code with full security audit trail 🔐

---

## 🏗️ Architecture

### Workflow Structure

```
Exercise 1: Simple Pipeline
└─ PHASE 1: specify
   └─ GATE: review-spec
   └─ PHASE 2: plan
   └─ GATE: review-plan
   └─ PHASE 3: tasks → implement

Exercise 2: Enterprise Pipeline
├─ PHASE 1: specify + fan-out reviews
│  ├─ Review 1: Security & Data Protection (parallel)
│  ├─ Review 2: Edge Cases & Failure Modes (parallel)
│  └─ GATE: review-spec → respecify
├─ PHASE 2: plan + cross-check
│  └─ GATE: review-plan
└─ PHASE 3: tasks → implement → audit → remediate
   ├─ Dependency Audit (NuGet MCP)
   ├─ Remediation Loop (reviewer ↔ developer)
   └─ GATE: sign-off
```

### Agents

**qa-advisor** (.github/agents/qa-advisor.agent.md)
- Security & data protection review
- Edge cases & failure modes analysis
- Threat modeling
- Runs in parallel during Phase 1

**developer** (.github/agents/developer.agent.md)
- Implements features from tasks.md
- Applies fixes from reviewer findings
- Writes tests (TDD)
- Runs during Phase 3

### Configuration Files

```
.specify/
├── workflows/
│   └── speckit/
│       └── workflow.yml (main spec-kit definition)
├── memory/               (agent state & context)
├── templates/           (artifact templates)
└── scripts/             (helper scripts)

.github/
├── workflows/
│   ├── speckit-workflow.yml (Exercise 1)
│   ├── exercise-2-secure-feature.yml (Exercise 2)
│   ├── exercise-3-multiservice.yml (Exercise 3 - TBD)
│   ├── dependency-management.yml (TBD)
│   └── release-deployment.yml (TBD)
└── agents/
    ├── qa-advisor.agent.md (reviewer)
    └── developer.agent.md (implementer)
```

---

## 🔐 Security & Configuration

### GitHub Token Setup

**GH_TOKEN (Required)**
Personal access token with full repo access.

1. Go to GitHub **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Create new token with scopes:
   - `repo` (full control)
   - `workflow` (Actions)
   - `gist` (for memory/artifacts)
3. Copy token
4. Go to repo **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
5. Name: `GH_TOKEN` | Value: `<your-token>`

**GitHub Copilot (Required)**
1. Activate [2-month free trial](https://github.com/settings/copilot)
2. Or subscribe to GitHub Copilot ($20/month)
3. Verify with: `gh copilot` (should work)

### Environment Variables

Set in workflow or locally:

```bash
# Copilot headless mode
export SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS="--allow-all-tools"

# GitHub authentication
export GH_TOKEN="github_pat_xxxxx"
export GITHUB_TOKEN="$GH_TOKEN"  # Actions uses this
```

---

## 📊 Workflow Outputs

### Exercise 1 Output (specs/ directory)

```
specs/001-feature-name/
├── spec.md              # Requirements, user stories, acceptance criteria
├── plan.md              # Implementation strategy, phases, timeline
├── tasks.md             # Task breakdown, dependencies, estimates
├── data-model.md        # Database schema (if needed)
├── contracts/           # API contracts, schemas
└── checklists/          # Feature checklist, QA checklist
```

### Exercise 2 Output (specs/ + artifacts)

Same as Exercise 1, plus:

```
specs/001-feature-name/
├── review-security.md               # Security findings & recommendations
├── review-edge-cases.md             # Edge cases, failure modes, mitigations
├── implementation.log               # Build & test logs
├── dependency-audit-report.json     # CVE vulnerabilities found
└── remediation-loop-summary.md      # Issues found & fixed
```

### Artifact Downloads

After workflow completes:
1. Go to workflow run
2. Scroll to **Artifacts** section
3. Download:
   - `phase-1-spec` (Phase 1 outputs)
   - `phase-2-plan` (Phase 2 outputs)
   - `phase-3-final` (Phase 3 outputs + audits)

---

## 🛠️ Local Development

### Setup

```bash
# Clone & navigate
git clone https://github.com/MerlinDalla/ai-spec-driven-development.git
cd ai-spec-driven-development

# Install specify CLI
npm install -g specify

# Verify installation
specify --version  # Should show 0.9.5+

# Setup Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .

# Setup database (optional, for local testing)
docker-compose up -d
alembic upgrade head
```

### Running Exercises Locally

```bash
# Exercise 1 simulation
specify workflow run speckit -i spec="Your feature description"

# This will:
# 1. Generate spec.md
# 2. Ask for review (interactive mode)
# 3. Generate plan.md
# 4. Ask for review
# 5. Generate tasks.md
# 6. Start implementation
```


## ✅ Verification Checklist

### Before Running Exercises
- [ ] GH_TOKEN secret configured
- [ ] GitHub Copilot enabled (free trial or paid)
- [ ] Repository accessible
- [ ] Node.js 20+ installed
- [ ] specify CLI installed (`npm install -g specify`)

### After Exercise 1 Completes
- [ ] spec.md generated with requirements
- [ ] plan.md generated with strategy
- [ ] tasks.md generated with breakdown
- [ ] All 3 artifacts downloadable
- [ ] No linting errors in specs

### After Exercise 2 Completes
- [ ] Phase 1: Spec + reviews generated
- [ ] Phase 2: Plan generated + consistency checked
- [ ] Phase 3: Tasks generated
- [ ] Dependency audit completed
- [ ] Remediation loop executed (if issues found)
- [ ] All artifacts downloadable
- [ ] Summary report generated

---


## 🐛 Troubleshooting

### Error: "specify CLI not found"
```bash
npm install -g specify
specify --version
```

### Error: "GH_TOKEN not configured"
1. Go to repo **Settings** → **Secrets and variables** → **Actions**
2. Verify `GH_TOKEN` exists
3. If not, create it: **New repository secret** → `GH_TOKEN` → `github_pat_xxxxx`

### Error: "Copilot free trial expired"
1. Go to [github.com/settings/copilot](https://github.com/settings/copilot)
2. Activate free trial again OR upgrade to paid subscription ($20/month)

### Error: "tests/speckit directory not found"
The workflow creates this automatically. If missing:
```bash
mkdir -p tests/workflow tests/run tests/speckit
```

### Workflow times out
Increase timeout in workflow YAML:
```yaml
timeout-minutes: 30  # Increase from default 360
```

---

## 📚 Resources

- **Spec-Kit Docs:** [github.com/github/copilot-cli](https://github.com/github/copilot-cli)
- **Specify CLI:** [npm package](https://www.npmjs.com/package/specify)
- **GitHub Copilot:** [github.com/features/copilot](https://github.com/features/copilot)
- **FastAPI:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **SQLAlchemy Async:** [sqlalchemy.org/asyncio](https://sqlalchemy.org/asyncio)

---

## 📝 License

MIT — See LICENSE file

---



