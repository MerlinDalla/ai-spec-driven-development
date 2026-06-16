# Workflows with Human Gates — Hands-On Exercises

RBAL · SPEC-KIT TRAINING · DAY 2

Run the built-in pipeline, then build your own — a fan-out, a custom agent on MCP, and a reviewer→fixer remediation loop, gated by humans.

---

## Slide 1 — Title

**Workflows with Human Gates — Hands-On Exercises**

Run the built-in pipeline, then build your own — a fan-out, a custom agent on MCP, and a reviewer→fixer remediation loop, gated by humans.

---

## Slide 2 — Exercise 1 · Goal: Built-in workflow — feel the gates

**WHAT WE WANT TO ACHIEVE**

**The shift: operator → supervisor**

- Run a pipeline that does specify → plan → tasks → implement by itself.
- It STOPS at two human gates — you judge, you don't type every command.
- State survives a closed terminal — a paused run resumes from the exact step.
- Needs no setup beyond one flag — the workflow ships with spec-kit.

---

## Slide 3 — Exercise 1 · Do this FIRST: Let the headless agent write files

The workflow runs Copilot headless. Without this, a step writes nothing — it just asks for approval it can never get.

```
PS> $env:SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS="--allow-all-tools"   # Windows (PowerShell)
$   export SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS="--allow-all-tools"  # macOS / Linux
    # appends --allow-all-tools to every copilot call in the workflow
```

**⚠ Symptom if you skip it**
- The specify step prints: `"I need your approval to create files…"`
- …and the specs/ folder never appears — yet the workflow still advances to the gate.

**Banking note**
- In production, drop the blanket flag.
- Use a precise allowlist instead: `--allow-tool nuget...` + read-only token.
- Least privilege — the gate is the safety net.

---

## Slide 4 — Exercise 1 · How: Run it, then practice the gate

```
$ specify workflow info speckit
$ specify workflow run speckit -i spec="<your feature, plain English>"
  → runs /specify, then STOPS at gate review-spec (prints run_id)
```

**APPROVE**
- Read the artifact
- Choose [1] approve
- Flows to the next phase

**FIX-IN-PAUSE**
- Don't approve yet
- Edit the file while it waits
- THEN approve — fix flows on

**REJECT = ABORT**
- Choose [2] reject
- Run ends 'aborted'
- For 'fundamentally wrong'

---

## Slide 5 — Exercise 1 · Try it: Run it on this feature

**FEATURE — CHANGE A CARD'S DAILY SPENDING LIMIT**

A customer changes the daily spending limit on their card. Increases above a configured ceiling require a second approval. The new limit takes effect on the next business day; same-day spending still uses the old limit. Every change is audit-logged with old value, new value, who and when. Negative or zero limits are rejected. Lost/expired cards are out of scope.

```
$ specify workflow run speckit -i spec="A customer changes the daily
  spending limit on their card; increases above a ceiling need a second
  approval; new limit applies next business day, same-day uses old limit;
  every change is audit-logged (old, new, who, when); reject zero or
  negative limits; lost or expired cards out of scope"
```

---

## Slide 6 — Exercise 2 · Goal: Your own: fan-out + custom agent + a fix loop

Orchestration is an artifact you design. Your workflow must include:

**Five required ingredients**
- ≥ 3 human gates at the decision points — and defend why not more.
- a fan-out that runs a step per item (custom agent, parallel reviews).
- a custom agent invoked as a command step (via --agent), not just a prompt.
- that agent using MCP (NuGet vulnerability audit) before the merge gate.
- a remediation loop: reviewer finds → developer fixes → reviewer verifies.

---

## Slide 7 — Exercise 2 · The plan: Four steps, in this order

Each step depends on the previous one — MCP must be up before the agent can audit; the agents must exist before the workflow can call them.

```
PS> $env:SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS="--allow-all-tools"   # step 0 — Windows (PowerShell)
$   export SPECKIT_INTEGRATION_COPILOT_EXTRA_ARGS="--allow-all-tools"  # step 0 — macOS / Linux
```

1. **NuGet MCP** — Stand up the NuGet MCP server (via dnx) and wire it into the Copilot CLI.
2. **Two agents** — Reviewer speckit.qa-advisor (finds, delegates) + fixer developer (writes code). Files go in .github/agents/.
3. **Workflow .yml** — Author the pipeline (types: command · prompt · fan-out · fan-in · gate · shell), then specify workflow add.
4. **Run** — specify workflow run rbal-secure-feature — watch the log for fan-out + MCP + delegation.

---

## Slide 8 — Exercise 2 · The target: The pipeline you're building

13 steps · 3 human gates · read left → right.  Green = stock spec-kit · ★ = you add this.  You author it as a .yml and register it with `specify workflow add`.

**PHASE 1 · SPEC** *(what & why)*
- specify
- ★ fan-out: qa-advisor ×2  (security · edge-cases)
- respecify
- → GATE 1 — review spec

**PHASE 2 · PLAN** *(how)*
- plan
- analyze  (cross-check spec vs plan)
- → GATE 2 — review plan

**PHASE 3 · BUILD & SECURE** *(build, then audit deps)*
- tasks · implement
- ★ dep-audit: NuGet MCP  (+ reviewer→fixer loop)
- → GATE 3 — sign off → merge

★ You add exactly two things: the fan-out reviews (Phase 1) and the dep-audit + reviewer→fixer loop (Phase 3). Everything else is stock spec-kit. The 3 orange gates are where you stop and judge — approve to flow on, reject = abort.

---

## Slide 9 — Exercise 2 · Step 1 · Setup (macOS): NuGet MCP for Copilot — check, install, add, verify

**①  Check .NET — you need 10.x**
```
dotnet --list-sdks        # look for a 10.x line, e.g. 10.0.301
```

**②  Install only if missing / wrong version**
```
# installer .pkg: dotnet.microsoft.com/download/dotnet/10.0  (pick Arm64 on Apple Silicon)
curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 10.0   # → installs to ~/.dotnet
```

**③  Add the NuGet MCP to Copilot  (DOTNET_ROOT is required — derive it from dnx)**
```
DNX="$(command -v dnx)"
copilot mcp add nuget --env DOTNET_ROOT="$(dirname "$DNX")" \
  -- "$DNX" NuGet.Mcp.Server --source https://api.nuget.org/v3/index.json --yes
```

**④  Verify**
```
copilot mcp list          # → nuget (local)
copilot mcp get nuget     # Environment must show DOTNET_ROOT
```

---

## Slide 10 — Exercise 2 · Step 1 · Setup (Windows): NuGet MCP for Copilot — check, install, add, verify

**①  Check .NET — you need 10.x**
```
dotnet --list-sdks        :: look for a 10.x line, e.g. 10.0.301
```

**②  Install only if missing / wrong version  (winget)**
```
winget install Microsoft.DotNet.SDK.10
:: open a NEW terminal afterwards (PATH refresh), then re-run  dotnet --list-sdks
```

**③  Add the NuGet MCP to Copilot  (DOTNET_ROOT derived from dnx)**
```
$dnx = (Get-Command dnx).Source
copilot mcp add nuget --env "DOTNET_ROOT=$(Split-Path $dnx)" -- $dnx NuGet.Mcp.Server --source https://api.nuget.org/v3/index.json --yes
```

**④  Verify**
```
copilot mcp list          :: -> nuget (local)
copilot mcp get nuget     :: Environment must show DOTNET_ROOT
```

**Why DOTNET_ROOT:** the MCP subprocess only inherits PATH from Copilot — so it finds dnx, but NOT the .NET runtime unless DOTNET_ROOT points at your .NET folder. Deriving it from dnx is correct for every install. Config file: `%USERPROFILE%\.copilot\mcp-config.json`.

---

## Slide 11 — Exercise 2 · Step 2: Two agents: a reviewer and a fixer

Copilot agents live in `.github/agents/`. You create two:

**REVIEWER — speckit.qa-advisor** *(finds & verifies - never writes code)*
- Reviews spec; audits NuGet via MCP.
- tools: must list the nuget MCP tools + task, list_agents, read_agent (to delegate).
- NO file-writing tools -> can't fix itself.
- speckit. namespace (needed for command:).

**FIXER — developer** *(changes the code - the only writer)*
- Applies the fix (edits files, runs build).
- NO tools: restriction -> full toolset.
- description says 'applies fixes' so the runtime delegates to it for that intent.
- Invoked at runtime - no speckit. prefix.

```
$ copilot -p "List the MCP tools from the nuget server." --allow-all-tools
  # -> nuget-review_supply_chain_security, nuget-fix_vulnerable_packages (and more)
```

**To run the MCP audit:** put those nuget tool names in the reviewer's `tools:`. To delegate: add `task, list_agents, read_agent` AND tell it in its instructions to 'delegate the fix to the developer sub-agent' (task = runSubagent in VS Code Chat).

---

## Slide 12 — Exercise 2 · Step 3a: Workflow anatomy — the step types

A workflow is YAML: a header (workflow / requires / inputs) + a list of steps. Every step has a type:

| type | what it does | key fields |
|---|---|---|
| `command` | calls an agent directly via --agent speckit.<name> — leaner, needs the speckit.* namespace | `command:` · `input.args` |
| `prompt` | delegates the task in text — works with any agent name, but adds a hop | `prompt:` |
| `fan-out` | one step → N branches, one per item in items: (same agent, args vary by {{ item }}) | `items:` · `step:` |
| `fan-in` | waits for every fan-out branch and gathers the results | `wait_for:` |
| `gate` | the human gate — pauses the pipeline for a decision | `message:` · `options:` · `on_reject:` |
| `shell` | runs a shell command | `run:` |

---

## Slide 13 — Exercise 2 · Step 3b: Author the workflow — the shape, then register & run

Skeleton only — you write the rest yourself: the 3 gates, plan/analyze, tasks/implement and the dep-audit step. (Full shape = the target slide; field reference = the step-types slide.)

```yaml
schema_version: "1.0"
workflow:
  id: "rbal-secure-feature"     # run this id, not the file
  name: "RBAL Secure Feature Pipeline"
requires:
  speckit_version: ">=0.7.2"
  integrations:
    any: ["copilot"]
inputs:
  spec:
    type: string
    required: true
  integration:
    type: string
    default: "copilot"          # every step inherits this
  project:
    type: string
    default: "transfer-service/transfer-service.csproj"
steps:
  - id: specify
    command: speckit.specify
    integration: "{{ inputs.integration }}"
    input:
      args: "{{ inputs.spec }}. Security-aware."
  - id: reviews                 # FAN-OUT (the pattern to copy)
    type: fan-out
    items:
      - "security & data protection"
      - "edge cases & failure modes"
    step:
      id: review
      type: command
      command: speckit.qa-advisor
      integration: "{{ inputs.integration }}"
      input:
        args: "Review spec.md for the '{{ item }}' angle."
  - id: gather                  # FAN-IN
    type: fan-in
    wait_for: [reviews]
  # ... now YOU add: gates, plan, analyze, tasks, implement, dep-audit, sign-off
```

```
$ specify workflow add rbal-ultimate.yml       # register (file name is free; run by workflow.id)
$ specify workflow run rbal-secure-feature -i spec="<your feature>"
```

---

## Slide 14 — Exercise 2 · Step 4: Run it on this feature

**FEATURE — OUTBOUND PAYMENT WITH SANCTIONS SCREENING**

A customer sends a payment to an external account. Before settlement it is screened against a sanctions list; a hit puts it on hold for manual review instead of settling. On clear, both balances change atomically. Amounts in minor units. Every decision (cleared, held, rejected) is audit-logged. Insufficient funds and closed accounts are rejected. Cross-currency out of scope.

```
# --allow-all-tools already set (Step 0, Windows or mac/Linux). Then:
$ specify workflow run rbal-secure-feature -i spec="<feature above>"
```

Two proofs in the log:
```
▸ speckit.qa-advisor …   ● review_supply_chain_security (MCP: nuget)     ← fan-out + MCP
● Developer …   └ Agent started in background                          ← reviewer delegated the fix
```

---

## Slide 15 — Exercise 2 · Debrief: Operator → supervisor

**fan-out / fan-in**
- one step → N branches, gathered by fan-in.
- Not faster — max_concurrency is a no-op; it runs sequentially today.

**command vs prompt**
- command = direct --agent select (speckit.*).
- prompt = delegate by text, any agent, +hop.

**MCP in the agent**
- Least privilege — the reviewer carries only nuget + task. Only the fixer writes code.

**the remediation loop**
- Reviewer finds & verifies, developer changes the code, the human signs off at the gate.
- Three roles the pipeline coordinates.
