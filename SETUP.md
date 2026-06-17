# Setup Guide — Spec-Kit Workflows

Complete setup instructions for running spec-kit exercises and workflows.

## 📋 Prerequisites

### Required
- GitHub account (with or without Copilot)
- Git client
- Node.js 20+ (`node --version`)
- Python 3.12 (`python --version`)
- Docker (for local database)

### Optional
- VS Code (recommended editor)
- Postman/Insomnia (API testing)
- DBeaver (database exploration)

---

## 1️⃣ GitHub Configuration

### Step 1: Create Personal Access Token (PAT)

1. Go to **GitHub** → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Set name: `Spec-Kit Workflows`
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
   - ✅ `gist` (Create gists)
   - ✅ `read:org` (Read org data)
5. Click **Generate token**
6. **Copy the token** (you won't see it again)

### Step 2: Configure Repository Secret

1. Go to your repository **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `GH_TOKEN`
4. Value: `paste your PAT`
5. Click **Add secret**

**Verify:**
```bash
# In repository terminal
echo $GH_TOKEN  # Should show your token (masked in logs)
```

### Step 3: Enable GitHub Copilot

1. Go to **GitHub** → **Settings** → **Copilot** → **Copilot** 
2. If free trial available: Click **Start your free trial**
3. If trial expired: Click **Subscribe** ($20/month)
4. Activate

**Verify:**
```bash
# In terminal
gh copilot
# Should show: The GitHub CLI Copilot commands are available.
```

---

## 2️⃣ Local Environment Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-spec-driven-development.git
cd ai-spec-driven-development
```

### Step 2: Install Node.js Dependencies

```bash
# Install specify CLI globally
npm install -g specify

# Verify
specify --version
# Should show: 0.9.5 or higher
```

### Step 3: Setup Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Step 4: Setup Database (Optional)

```bash
# Start PostgreSQL via Docker
docker-compose up -d

# Wait for database to be ready (10-15 seconds)
sleep 15

# Run migrations
alembic upgrade head

# Verify
psql postgresql://fund_transfer:fund_transfer_pass@localhost:5432/fund_transfer_test -c "SELECT 1;"
# Should show: 1
```

---

## 3️⃣ Environment Variables

### Terminal Setup

```bash
# Set for current terminal session
export GH_TOKEN="github_pat_xxxxx"
export GITHUB_TOKEN="$GH_TOKEN"
export SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS="--allow-all-tools"

# Verify
echo $GH_TOKEN  # Should show your token
```

### VS Code Setup

Create `.env.local` in project root:

```env
GH_TOKEN=github_pat_xxxxx
GITHUB_TOKEN=github_pat_xxxxx
SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS=--allow-all-tools
```

---

## 4️⃣ Directory Structure Verification

```bash
# Verify required directories exist
mkdir -p .specify/workflows/speckit
mkdir -p .github/agents
mkdir -p tests/workflow
mkdir -p tests/run
mkdir -p tests/speckit

# Verify key files
ls -la .github/workflows/
# Should show:
# - speckit-workflow.yml
# - exercise-2-secure-feature.yml
# - exercise-3-multiservice.yml
# - dependency-management.yml
# - release-deployment.yml

ls -la .github/agents/
# Should show:
# - qa-advisor.agent.md
# - developer.agent.md
```

---

## 5️⃣ Workflow Configuration

### Configure Agents

Edit `.specify/workflows/speckit/workflow.yml`:

```yaml
agents:
  - name: qa-advisor
    role: reviewer
    reviews:
      - security
      - edge-cases
      
  - name: developer
    role: implementer
    capabilities:
      - code-generation
      - testing
```

### Configure Environment

Edit `.specify/scripts/config.sh`:

```bash
#!/bin/bash
export PROJECT_NAME="Fund Transfer Service"
export GITHUB_ORG="YOUR_ORG"
export GITHUB_REPO="ai-spec-driven-development"
export GH_TOKEN="${GH_TOKEN}"
export PYTHON_VERSION="3.12"
```

---

## 6️⃣ Test the Setup

### Test 1: Verify CLI Tools

```bash
# Check all tools
node --version      # v20.x.x
python --version    # Python 3.12.x
git --version       # git version 2.x
gh --version        # gh version x.x.x
specify --version   # 0.9.5+

echo "✅ All tools installed"
```

### Test 2: Test GitHub Authentication

```bash
# Verify token works
gh auth status
# Should show: ✓ Authenticated to github.com

# Test API access
gh repo view
# Should show your repository details
```

### Test 3: Test Copilot

```bash
# List available Copilot commands
gh copilot --help
# Should show: GitHub CLI Copilot commands

# Test suggestion (optional)
gh copilot suggest "list all files in git"
```

### Test 4: Test Database (if using)

```bash
# Check PostgreSQL is running
docker ps | grep postgres
# Should show: postgres container running

# Test connection
python -c "
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect('postgresql://fund_transfer:fund_transfer_pass@localhost:5432/fund_transfer_test')
    result = await conn.fetchval('SELECT 1')
    await conn.close()
    return result

print('✅ Database connected' if asyncio.run(test()) == 1 else '❌ Connection failed')
"
```

---

## 7️⃣ Running Your First Exercise

### Exercise 1: Built-in Pipeline

```bash
# Option A: Via GitHub Actions (easiest)
# 1. Go to: https://github.com/YOUR_USERNAME/ai-spec-driven-development/actions
# 2. Select: "Exercise 1 · Built-in Spec-Kit Pipeline"
# 3. Click: "Run workflow"
# 4. Input feature: "A customer can create a recurring transfer..."
# 5. Watch the pipeline execute

# Option B: Local simulate (requires specify CLI)
mkdir -p tests/workflow tests/run tests/speckit
cp -r .specify tests/.specify
cp -r .specify/workflows/* tests/workflow/

cd tests/workflow
specify workflow run speckit -i spec="Your feature description"
cd ../..
```

### Exercise 2: Enterprise Pipeline

```bash
# Go to GitHub Actions
# 1. Select: "Exercise 2 · Custom Workflow with Fan-Out, MCP..."
# 2. Input feature: "Users can set spending limits with caps..."
# 3. Workflow will:
#    - Phase 1: Generate spec + parallel reviews
#    - Phase 2: Generate plan + validation
#    - Phase 3: Generate tasks + implement + audit + remediate
```

---

## 🐛 Troubleshooting

### Issue: "specify: command not found"

```bash
# Solution 1: Install globally
npm install -g specify

# Solution 2: Use npm directly
npx specify --version

# Solution 3: Check PATH
echo $PATH
which specify
```

### Issue: "GH_TOKEN not found"

```bash
# Verify secret in GitHub
gh secret list
# Should show: GH_TOKEN

# Verify in terminal
echo $GH_TOKEN
# If empty, run:
export GH_TOKEN="github_pat_xxxxx"
```

### Issue: "Copilot not available"

```bash
# Check Copilot is enabled
gh copilot
# If error, go to: https://github.com/settings/copilot

# Activate free trial or subscription
# Then retry after 5 minutes
```

### Issue: "Database connection failed"

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# If not running, start it
docker-compose up -d

# If database doesn't exist, create it
docker exec -it postgres psql -U postgres -c "CREATE DATABASE fund_transfer_test;"

# Verify
psql postgresql://fund_transfer:fund_transfer_pass@localhost:5432/fund_transfer_test -c "SELECT 1;"
```

### Issue: "Python module not found"

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -e .

# Verify installed
pip list | grep fastapi
```

---

## ✅ Setup Checklist

- [ ] GitHub account created
- [ ] Personal Access Token (PAT) created and copied
- [ ] GH_TOKEN secret added to repository
- [ ] GitHub Copilot enabled (free trial or paid)
- [ ] Node.js 20+ installed
- [ ] Python 3.12 installed
- [ ] Repository cloned locally
- [ ] specify CLI installed (`npm install -g specify`)
- [ ] Python virtual environment created and activated
- [ ] Dependencies installed (`pip install -e .`)
- [ ] Database setup completed (if needed)
- [ ] `.env.local` file created with environment variables
- [ ] All tools verified (node, python, git, gh, specify)
- [ ] GitHub authentication working (`gh auth status`)
- [ ] Copilot working (`gh copilot --help`)
- [ ] Test directory structure created
- [ ] Ready to run Exercise 1 ✅

---

## 📚 Next Steps

1. **Run Exercise 1** — Build confidence with the basic pipeline
2. **Run Exercise 2** — Experience the enterprise workflow
3. **Customize Agents** — Modify `.github/agents/` for your needs
4. **Configure Workflows** — Tailor `.specify/` for your conventions
5. **Enable All Exercises** — Set up Exercise 3, dependency management, and releases

---

## 🆘 Support

### Get Help
1. Check troubleshooting section above
2. Read README.md for overview
3. Review agent documentation in `.github/agents/`
4. Check GitHub issue #1 for FAQs

### Report Issues
1. Create issue on GitHub with:
   - Error message
   - Steps to reproduce
   - Environment details (OS, Node version, Python version)
2. Include relevant logs from GitHub Actions or terminal

---

**Last Updated:** June 17, 2026  
**Status:** Complete ✅
