# solution-tradeoff

[![CI](https://github.com/JanvandenBrand/solution-tradeoff-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/JanvandenBrand/solution-tradeoff-tool/actions/workflows/ci.yml)

A command-line tool for structured, multi-stakeholder solution trade-off analysis with Claude.

You describe an architecture decision (the question, the candidate solutions, the stakeholders
who should weigh in) and supply a requirements spreadsheet. The tool generates one prompt per
stakeholder perspective — architecture, security, data protection, finance, operations and so on —
each with the same shared context and a fixed budget of priority points. Every perspective scores
the candidates independently and returns validated YAML; a final compile step turns those
responses into a trade-off analysis document.

Runs fully automated through the Claude API, or manually by pasting the prompts into Claude Chat.

The tool enforces one rule above all: **nothing is built until every selected stakeholder
perspective has been explicitly verified by a real person.** The AI plays the stakeholders;
a human confirms each stakeholder definition is right.

## Quickstart

Requires Python 3.11+ and [Poetry](https://python-poetry.org/) 2.x.

```bash
git clone https://github.com/JanvandenBrand/solution-tradeoff-tool.git
cd solution-tradeoff-tool
poetry install
cp decision.yaml.example decision.yaml
poetry run solution-tradeoff list-perspectives
poetry run solution-tradeoff verify-perspective --id architecture   # repeat for each perspective in decision.yaml
poetry run solution-tradeoff build-prompts --xlsx examples/requirements_sample.xlsx
```

The prompts are now in `outputs/AD-001/`. Continue with [Running the Analysis](#running-the-analysis).

## Origin

Built for architecture decision-making in INDICATE, an EU-funded
project (Grant 101167778) building a federated ICU data infrastructure. The bundled perspectives
reflect that setting — a multi-organisation health data platform — and are meant as a starting
point: edit them, or replace them with your own.

---

## How It Works

```
CLI (automated)                      CLI (manual fallback)
──────────────────────────           ─────────────────────────────

1. Set up and verify             →   1. Set up and verify
   perspectives                         perspectives

2. Build prompt package          →   2. Build prompt package
   (build-prompts)                      (build-prompts)

3. Run perspective sessions      →   3. Per stakeholder: paste agent
   (run-perspectives)                   prompt into Claude Chat
   → YAML responses saved              → save YAML response manually

4. Compile analysis              →   4. Add YAMLs to project
   (run-compile)                        knowledge + paste compile prompt
   → analysis.md
```

---

## Installation

**Prerequisites:** Python 3.11+, `pyenv`, Poetry 2.x (`pipx install poetry`)

> Always use a virtual environment. Never install this tool into your system Python.
> The steps below use `pyenv` to manage the Python version and `poetry` to manage the
> virtual environment and dependencies. Do not skip these steps.

### 1 — Install the correct Python version

```bash
pyenv install 3.11.9          # install Python 3.11 if not already present
pyenv local 3.11.9            # pin this version for the project directory
python --version              # confirm: Python 3.11.9
```

### 2 — Clone and enter the repository

```bash
git clone https://github.com/JanvandenBrand/solution-tradeoff-tool.git
cd solution-tradeoff-tool
```

### 3 — Create and activate the virtual environment

```bash
poetry env use python         # create venv using the pyenv-pinned version
poetry install                # install all dependencies into the venv
eval $(poetry env activate)   # activate the venv in your current shell
```

You will see the venv name prefixed in your prompt.
**All subsequent commands in this manual assume this activated shell** — or prefix them with
`poetry run`.

To re-activate the venv in a new terminal session:

```bash
cd solution-tradeoff-tool
eval $(poetry env activate)
```

### 4 — Verify installation

```bash
solution-tradeoff --help
```

---

## First-Time Setup (do once per project)

### Step 1 — Check the existing config

The tool ships with `config.yaml` and `perspectives/` already populated. Review them
before starting any analysis:

```bash
cat config.yaml                      # column mappings, budget settings, output patterns
solution-tradeoff list-perspectives  # shows all perspective files and their status
```

`config.yaml` is version-controlled and shared. Do not change it unless the xlsx schema
changes (update `xlsx.columns` entries to match new column headers).

### Step 2 — Understand `config.yaml`

The key settings you may need to adjust:

```yaml
budget:
  multiplier: 2.5    # point budget = requirement_count × multiplier, rounded up
  round_to: 5
  minimum: 15

elimination:
  must_score_threshold: 6   # a candidate scoring < 6 on any Must is eliminated

output:
  agent_filename_pattern: "{index:02d}_{perspective}.md"
```

All xlsx column headers are defined under `xlsx.columns` and `xlsx.principles_columns`.
If the spreadsheet schema changes, update these values — no code changes needed.

### Step 3 — Review and extend perspective files

Perspective files already exist in `perspectives/` and match the required schema.
To add a new perspective, create `perspectives/{id}.yaml` with this structure:

```yaml
id: clinical                             # matches the filename (without .yaml)
label: "Clinical End-User Perspective"   # human-readable label
index: 1                                 # display order (must be unique)

role: >
  Write in second person, as if briefing the AI agent that will inhabit this
  perspective. Be specific: job title, institution type, relationship to the organisation,
  daily responsibilities. This field determines the quality of the evaluation.

primary_concern: >
  What this stakeholder cares about most.

failure_mode: >
  What a bad outcome looks like from this stakeholder's point of view.

evaluation_lens:
  - "Question 1 this stakeholder would ask when evaluating the solution"
  - "Question 2 ..."

# The following three fields are written by verify-perspective — do not set by hand
# verified: false
# verified_by: ~
# verified_at: ~
```

**Example — `perspectives/clinical.yaml`** (excerpt, already in the repository):

```yaml
id: clinical
label: "Clinical End-User Perspective"
index: 1

role: >
  You are a ward nurse and charge nurse in an ICU at a mid-sized European
  hospital that participates in a federated health data platform as a Data
  Provider. You are not a researcher. Your primary responsibility is patient
  care. You interact with clinical systems — EMR, monitoring systems, nursing
  documentation — continuously throughout your shift.

primary_concern: >
  Workflow disruption and cognitive load. Any change to clinical systems or
  processes that adds steps, introduces ambiguity, or requires training
  creates direct risk — not to the research programme, but to patient care.

failure_mode: >
  A solution that adds documentation burden, requires clinical staff to
  take actions they do not understand the purpose of, or that changes
  familiar workflows without adequate notice, training, or visible benefit
  to the care team.

evaluation_lens:
  - "Does this require any action from bedside clinical staff — and if so, is that burden justified and explained?"
  - "Does it change or depend on how clinical data is entered in the EMR or monitoring system?"
  - "Were clinical staff consulted during design, and do they understand what the platform does with their data?"
  - "Is there a clear, plain-language explanation of how patient data is protected that clinical staff can give to patients?"
```

List all current perspectives:

```bash
solution-tradeoff list-perspectives
```

Example output:

```
                 Perspectives
 Index  ID                Label                        Verified
 1      clinical          Clinical End-User Perspective    ✓
 2      data_management   Data Management Perspective      ✗
 3      data_scientist    Data Science Perspective         ✓
 ...
```

> Do **not** set `verified: true` by hand. Use the `verify-perspective` command (Step 4).

### Step 4 — Verify each perspective

Each perspective must be explicitly confirmed by the named contact before any analysis can run.
For each perspective file, call:

```bash
solution-tradeoff verify-perspective --id clinical
```

The command will:
1. Display the full perspective definition (label, role, primary concern, failure mode, evaluation lens)
2. Ask you to confirm that the named contact has reviewed and agreed to the definition
3. Record your confirmation with a timestamp and your identity
4. Write the `verified`, `verified_by`, and `verified_at` fields into the perspective file

**Example session:**

```
$ solution-tradeoff verify-perspective --id clinical

── Perspective: clinical ──────────────────────────────────────────────────
Label:           Clinical End-User Perspective
File:            perspectives/clinical.yaml

Role:
  You are a ward nurse and charge nurse in an ICU at a mid-sized European
  hospital that participates in a federated health data platform ...

Primary concern:
  Workflow disruption and cognitive load. Any change to clinical systems
  or processes that adds steps, introduces ambiguity, or requires training
  creates direct risk — not to the research programme, but to patient care.

Failure mode:
  A solution that adds documentation burden, requires clinical staff to
  take actions they do not understand the purpose of ...

Evaluation lens:
  1. Does this require any action from bedside clinical staff — and if so,
     is that burden justified and explained?
  2. Does it change or depend on how clinical data is entered in the EMR
     or monitoring system?
  3. Were clinical staff consulted during design, and do they understand
     what the platform does with their data?
  4. Is there a clear, plain-language explanation of how patient data is
     protected that clinical staff can give to patients?
───────────────────────────────────────────────────────────────────────────

Has the named contact reviewed and agreed to this perspective definition?
[y/N]: y

Verified by (your name): A. Architect

✓ Perspective 'clinical' marked as verified.
  Verified by: A. Architect on 2026-10-07
  Written to:  perspectives/clinical.yaml
```

Repeat for every perspective file. Check status at any time:

```bash
solution-tradeoff validate-config
```

**Example output when perspectives are not all verified:**

```
✗ Perspective 'infrastructure' is not yet verified.
  → run: solution-tradeoff verify-perspective --id infrastructure
✗ Perspective 'data_scientist' is not yet verified.
  → run: solution-tradeoff verify-perspective --id data_scientist

2 error(s). Build cannot start until all checks pass.
```

**Example output when all perspectives are verified:**

```
✓ perspectives/ directory found (12 files)
✓ decision.yaml valid (AD-001, 3 candidates, 9 perspectives selected)
✓ All checks passed. Build is ready to start.
```

---

## Running an Analysis

### Step 5 — Prepare your `decision.yaml`

All analysis inputs live in a single `decision.yaml` file. Copy the example and fill it in:

```bash
cp decision.yaml.example decision.yaml
```

**`decision.yaml` field reference:**

```yaml
decision:
  id: AD-001                      # Architecture Decision ID — used as output folder name
  name: "Research Data Storage Selection"
  problem_statement: >            # One sentence: what architectural choice must be made?
    Which storage service should the platform use for researcher project data in Plateau 1?
  planning_horizon: short         # short | medium | long
  plateau: 1                      # Filter requirements to this plateau and below (optional)

candidates:                       # 2–5 options being evaluated
  - id: A
    name: "Managed cloud object storage"
  - id: B
    name: "Self-hosted S3-compatible object store"
  - id: C
    name: "Institutional network file share"

perspectives:                     # Which stakeholder perspectives to include
  - architecture                  # Must match a filename in perspectives/ (without .yaml)
  - data_protection
  - data_scientist
  - devops
  - financial
  - governance
  - infrastructure
  - security

requirements_filter:
  domains:                        # Leave empty [] to include all domains
    - Technology
    - Security and Identity
  moscow:                         # MoSCoW levels to include
    - Must
    - Should

# Optional: governing Architecture Decisions for this analysis.
# Each entry is a free-text string — include the AD ID and a short title.
# These appear in 00_context.md under "Architecture Decisions".
architecture_decisions:
  - "AD-000: Cloud-first hosting — Closed"

# Optional: path to a Markdown file with narrative background knowledge for this
# decision (vendor calls, risk register notes, unresolved items). Resolved relative
# to this file's directory. Appended to 00_context.md as "## Background Knowledge",
# after everything else and before each perspective's own prompt.
background_knowledge_path: "background_knowledge.md"
```

You also need a requirements & principles spreadsheet (see
[Requirements spreadsheet](#requirements-spreadsheet)). The tool reads it via the `--xlsx` flag.
To try the tool, use the synthetic `examples/requirements_sample.xlsx`.

### Step 5b — Write the background knowledge (optional, recommended)

The requirements list tells the agents *what* matters; background knowledge tells them what you
already know about the candidates — vendor answers, constraints, verified facts, costs, open
questions. Start from the template:

```bash
cp templates/background_knowledge.md background_knowledge.md
```

Fill it in, then set `background_knowledge_path: "background_knowledge.md"` in `decision.yaml`.
Keep it factual and recommendation-free, and leave out anything you would not want sent to
an LLM provider. `background_knowledge.md` at the project root is git-ignored, like
`decision.yaml` and `outputs/`.

### Step 6 — Build the prompt package

One command reads `decision.yaml`, verifies all selected perspectives, filters the
requirements spreadsheet, and writes the full prompt package:

```bash
solution-tradeoff build-prompts \
  --decision decision.yaml \
  --xlsx /path/to/requirements_and_principles.xlsx
```

To validate inputs without writing any files:

```bash
solution-tradeoff build-prompts \
  --decision decision.yaml \
  --xlsx /path/to/xlsx \
  --dry-run
```

**What this does:**
- Runs all pre-flight checks (fails immediately if any selected perspective is unverified)
- Loads and filters the requirements spreadsheet
- Loads all Architecture Principles from the xlsx (all principles included, not filtered by domain)
- Includes Architecture Decisions from `decision.yaml` (`architecture_decisions` field)
- Renders the context block (`00_context.md`) and one prompt file per perspective
- Writes a `review.md` checklist and `manifest.json` to `outputs/{decision_id}/`

**CLI output (dry-run):**

```
✓ Decision AD-001 loaded
✓ 8 requirements filtered (5 Must, 3 Should)
✓ 5 principles filtered
✓ 7 perspective agents prepared (point budget: 20)
  [dry-run] No files written.
```

**CLI output (full run):**

```
✓ Decision AD-001 loaded
✓ 8 requirements filtered (5 Must, 3 Should)
✓ 5 principles filtered
✓ 7 perspective agents prepared (point budget: 20)
✓ Output written to outputs/AD-001/
  → Review:   outputs/AD-001/review.md
  → Manifest: outputs/AD-001/manifest.json
  → Compile:  outputs/AD-001/compile-prompt.md
```

**Before continuing:** open `outputs/{decision_id}/review.md` and work through the
checklist:
- Is the problem statement accurate?
- Are the candidates correctly named?
- Are the requirement counts right (Must vs Should)?
- Is the point budget reasonable?

If anything is wrong: edit `decision.yaml` and re-run. The command is idempotent —
safe to run multiple times (`--force` is not required to overwrite).

**Structure of the generated output:**

```
outputs/AD-001/
├── review.md                    ← Verification checklist — read this first
├── manifest.json                ← Machine-readable index of all agent files
└── agents/
    ├── 00_context.md            ← Shared context block (use as Claude Chat project instruction)
    ├── 01_architecture.md       ← One file per perspective, numbered by index
    ├── 02_data_protection.md
    ├── ...
    └── 10_synthesis.md          ← Synthesis agent prompt
```

**Structure of `00_context.md` (the context block):**

```markdown
## Decision context
- Decision ID: AD-001
- Decision name: Research Data Storage Selection
- Problem statement: ...
- Planning horizon: short
- Plateau filter: 1

## Candidate solutions under evaluation
- Option A: Managed cloud object storage
- Option B: Self-hosted S3-compatible object store
- Option C: Institutional network file share

## Architecture Principles (N)
| Ref | Description | Domain |
...
[all principles from the xlsx Principles sheet — always included]

## Architecture Decisions (N)
- AD-000: Cloud-first hosting — Closed
[only present if architecture_decisions is set in decision.yaml]

## Applicable requirements — Must (65)
| Req ID | Requirement | Domain | APR Ref | AD Ref |
...

## Applicable requirements — Should (8)
| Req ID | Requirement | Domain | APR Ref | AD Ref |
...
[only present if Should requirements are included]

## Point budget
You have 180 priority points to distribute across the 73 criteria above.

## Background Knowledge
[contents of the file at background_knowledge_path, verbatim]
[only present if background_knowledge_path is set in decision.yaml — appended last]
```

**Before opening any Claude Chat session:** open `outputs/{decision_id}/agents/00_context.md` and verify:
- All relevant requirements are included
- APR and AD references are present where expected; missing refs show as `—`

**Before opening each perspective session:** open the individual agent file and verify:
- The stakeholder identity block is correct (role, primary concern, failure mode)
- The point budget instruction is present
- The YAML output schema is at the bottom of the file

---

## Running the Analysis

There are two ways to run the analysis: **automated** (recommended) and **manual** (Claude Chat).

---

### Automated path (Steps 7–9)

Set `ANTHROPIC_API_KEY` in your environment before running:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**Step 7 — Run all perspective sessions:**

```bash
solution-tradeoff run-perspectives \
  --output-dir outputs/AD-001 \
  --responses-dir outputs/AD-001/responses
```

This calls the Claude API once per perspective file, saves each YAML response to
`--responses-dir`, and validates it immediately. Output:

```
  02_data_scientist.md ... ✓
  04_data_protection.md ... ✓
  05_security.md ... ✗ 1 error(s):
       must_challenges.1.req_id: None is not of type 'string'
  ...

⚠ 1/9 response(s) invalid — review files in outputs/AD-001/responses/ and re-run those sessions.
```

Invalid files are saved as-is. Fix the YAML manually (see troubleshooting) and re-validate:

```bash
solution-tradeoff validate-yaml --responses-dir outputs/AD-001/responses/
```

To rerun just the perspective(s) that failed or never completed, without re-calling the API
for everything else, pass `--perspective <id>` (repeatable — the id is the bare perspective
name, e.g. `security`, not the numbered filename):

```bash
solution-tradeoff run-perspectives \
  --output-dir outputs/AD-001 \
  --responses-dir outputs/AD-001/responses \
  --perspective security
```

This overwrites only `outputs/AD-001/responses/security.yaml`; every other response file is
left untouched. Pass `--perspective` more than once to rerun several at a time. An unknown id
fails immediately with the list of available ids, before any API call is made.

**Step 8 — Compile the analysis:**

```bash
solution-tradeoff run-compile \
  --output-dir outputs/AD-001 \
  --responses-dir outputs/AD-001/responses
```

This fills the `compile-prompt.md` placeholders with the actual YAML responses, calls
the Claude API, and writes the result to `outputs/AD-001/analysis.md`.

```
  Calling Claude API for compile step ... ✓
✓ Analysis written to outputs/AD-001/analysis.md
```

To write the analysis to a different path:

```bash
solution-tradeoff run-compile \
  --output-dir outputs/AD-001 \
  --responses-dir outputs/AD-001/responses \
  --output reports/AD-001-tradeoff.md
```

---

### Manual path (Claude Chat)

Use this if you prefer to run sessions interactively or want to inspect each response
before saving.

**Step 7 — Set up the Claude Chat project:**

1. Open [claude.ai](https://claude.ai) and open (or create) a project for this decision
2. Go to **Project Settings → Project Instructions**
3. Paste the entire contents of `outputs/{decision_id}/agents/00_context.md`
   as the project instruction

**Step 8 — Run one session per perspective:**

For each numbered agent file in `outputs/{decision_id}/agents/`:

1. Open a **new chat** inside that project
2. Copy the entire contents of the perspective file (e.g. `02_data_scientist.md`)
3. Paste it into the chat and send
4. The chat will respond with a YAML block
5. Copy the YAML and save it (e.g. `outputs/AD-001/responses/data_scientist.yaml`)

> Run sessions **independently** — each session must not see another session's output.
> Claude Chat limits the number of concurrent chats, so you may need to run them in batches.

Validate each YAML before continuing:

```bash
solution-tradeoff validate-yaml --responses-dir outputs/AD-001/responses/
```

**Step 9 — Compile:**

1. Go to **Project Knowledge** in your Claude Chat project
2. Add each validated YAML response file
3. Open a new chat and paste the contents of `outputs/{decision_id}/compile-prompt.md`
4. Claude Chat will produce the trade-off analysis document

> **`must_challenges` with new requirements:** if the agent proposes a requirement not
> in the xlsx, it assigns a placeholder ID (`NEW-001`, `NEW-002`, …). If validation
> fails with `must_challenges.N.req_id: None is not of type 'string'`, the agent output
> `null` — edit the YAML to replace `null` with `"NEW-001"` and re-validate.

---

## Requirements spreadsheet

The tool reads requirements and architecture principles from one `.xlsx` file with two sheets,
`Requirements` and `Principles` (sheet names are set in `config.yaml`).
`examples/requirements_sample.xlsx` is a small synthetic example.

**Requirements sheet:**

| `config.yaml` key | Default xlsx column header |
|---|---|
| `req_id` | `Ref` |
| `description` | `Requirement` |
| `domain` | `Category` |
| `moscow` | `MoSCoW` |
| `plateau` | `Plateau` |
| `status` | `Status` |
| `apr_ref` | `APR Link` |
| `ad_ref` | `AD Ref` |

The `apr_ref` and `ad_ref` columns are **optional**. If absent, the tool logs a warning and
continues — missing values render as `—` in `00_context.md`.

Rows with status `Deprecated` or `Rejected` are skipped. Requirements are further filtered by
`requirements_filter` (domains, MoSCoW) and `plateau` from `decision.yaml`.

**Principles sheet:** `Ref`, `Architecture Principle`, `Category` (`xlsx.principles_columns`).
All principles are included in the context.

Architecture Decisions are **not** sourced from the xlsx. Define them in `decision.yaml`
under `architecture_decisions` (see Step 5).

If the xlsx schema changes, update `config.yaml` only — not the Python code.

---

## Command Reference

| Command | Description |
|---|---|
| `solution-tradeoff --help` | Show all commands |
| `solution-tradeoff validate-config` | Run all pre-flight checks and show status |
| `solution-tradeoff verify-perspective --id <id>` | Interactively verify a perspective |
| `solution-tradeoff list-perspectives` | List all perspectives and verification status |
| `solution-tradeoff build-prompts` | Build full prompt package from `decision.yaml` |
| `solution-tradeoff validate-yaml --responses-dir <dir>` | Validate all YAML response files in a directory; also flags byte-identical duplicates (a common copy-paste error) among valid files |
| `solution-tradeoff run-perspectives --output-dir <dir> --responses-dir <dir>` | Call Claude API for each perspective, save and validate YAML responses; add `--perspective <id>` (repeatable) to rerun only specific perspectives |
| `solution-tradeoff run-compile --output-dir <dir> --responses-dir <dir>` | Embed YAML responses into compile prompt and call Claude API |

### Common flags

| Flag | Commands | Description |
|---|---|---|
| `--decision <file>` | `build-prompts`, `validate-config` | Path to `decision.yaml` (default: `./decision.yaml`) |
| `--perspectives-dir <dir>` | `build-prompts`, `validate-config`, `list-perspectives`, `verify-perspective` | Path to perspectives directory (default: `./perspectives`) |
| `--xlsx <file>` | `build-prompts` | Path to requirements xlsx |
| `--config <file>` | `build-prompts` | Path to `config.yaml` (default: `./config.yaml`) |
| `--output <dir>` | `build-prompts` | Output directory root (default: `./outputs`) — **not** the same flag as `run-compile`'s `--output` below |
| `--dry-run` | `build-prompts` | Print summary; do not write files |
| `--force` | `build-prompts` | Overwrite existing output directory |
| `--id <id>` | `verify-perspective` | Perspective ID to verify |
| `--responses-dir <dir>` | `validate-yaml`, `run-perspectives`, `run-compile` | Directory containing YAML response files |
| `--schema <file>` | `validate-yaml`, `run-perspectives` | Path to JSON Schema (default: `./schemas/tradeoff-output.schema.json`) |
| `--output-dir <dir>` | `run-perspectives`, `run-compile` | Directory produced by `build-prompts` |
| `--output <file>` | `run-compile` | Path for analysis output (default: `<output-dir>/analysis.md`) — **not** the same flag as `build-prompts`'s `--output` above |
| `--model <model>` | `run-perspectives`, `run-compile` | Claude model ID (default: `claude-sonnet-5-5`) |
| `--perspective <id>` | `run-perspectives` | Perspective id to run (repeatable). Default: all perspectives in `agents/` |

---

## Troubleshooting

### "Build cannot start — perspective not verified"

One or more selected perspectives have `verified: false`. Run:

```bash
solution-tradeoff validate-config
```

The output lists which perspectives need verification and the exact command to run for each.

### "Required column not found in requirements xlsx"

All column mappings are in `config.yaml`. See [Requirements spreadsheet](#requirements-spreadsheet)
for the default headers.

### "Template token found in output"

Open the relevant `.j2` file in `templates/` and check for `{{ }}` blocks referencing
variables that are not passed by the builder. Check `builders/context.py` or
`builders/agent_prompt.py` for the variable names being passed to the template.

### "Perspective not found in perspectives/ directory"

The perspective ID in `decision.yaml` must exactly match a filename in `perspectives/`
(without `.yaml`). Run `solution-tradeoff list-perspectives` to see all available IDs.

### YAML validation fails with "additionalProperties"

The agent YAML schema (`schemas/tradeoff-output.schema.json`) disallows extra fields.
Remove any fields from the YAML that are not part of the defined schema. The allowed
top-level fields are: `perspective_id`, `concerns`, `point_allocations`, `must_challenges`,
`preferred_option`, `preferred_rationale`.

---

## File Inventory

| File | Managed by | Purpose |
|---|---|---|
| `config.yaml` | You | Column mappings, budget settings, output filename patterns |
| `decision.yaml` | You | Per-analysis config: decision, candidates, perspectives, filter |
| `decision.yaml.example` | Tool | Template for new analyses — copy and edit |
| `background_knowledge.md` | You | Optional per-decision briefing (git-ignored) |
| `templates/background_knowledge.md` | Tool | Template for `background_knowledge.md` — copy and fill in |
| `examples/requirements_sample.xlsx` | Tool | Synthetic requirements & principles spreadsheet |
| `perspectives/{id}.yaml` | You + tool | One file per perspective; `verified` fields written by `verify-perspective` |
| `schemas/tradeoff-output.schema.json` | Tool | JSON Schema (Draft 2020-12) for validating agent YAML output |
| `templates/context_block.md.j2` | Tool | Jinja2 template for `00_context.md` |
| `templates/perspective_agent.md.j2` | Tool | Jinja2 template for perspective prompt files |
| `templates/synthesis_agent.md.j2` | Tool | Jinja2 template for synthesis prompt file |
| `templates/compile-prompt.md.j2` | Tool | Jinja2 template — rendered automatically by `build-prompts` |
| `outputs/{id}/review.md` | Tool | Generated verification checklist — read before running sessions |
| `outputs/{id}/manifest.json` | Tool | Machine-readable index of all agent files |
| `outputs/{id}/compile-prompt.md` | Tool | Generated compile prompt — paste into Claude Chat after all YAMLs are collected |
| `outputs/{id}/agents/00_context.md` | Tool | Generated context block — use as Claude Chat project instruction |
| `outputs/{id}/agents/{N}_{perspective}.md` | Tool | Generated perspective prompt — paste into Claude Chat session |
| `outputs/{id}/responses/{perspective}.yaml` | Tool / You | YAML response per perspective — written by `run-perspectives` or saved manually |
| `outputs/{id}/analysis.md` | Tool | Final trade-off analysis — written by `run-compile` |

> `outputs/`, `decision.yaml`, `background_knowledge.md` and `*.xlsx` are git-ignored in this
> repository so that real decision material is never pushed by accident. In your own private
> fork you may want to version `decision.yaml` and `perspectives/*.yaml` — they record what
> was decided and who verified each perspective.

> The responses directory (e.g. `responses/`) is your choice — pass it to `validate-yaml`
> via `--responses-dir`. It is not created by the tool.

---

## Contributing

Issues and pull requests are welcome. Run `make check` (lint, type check, tests) before
opening a PR. `CLAUDE.md` describes the design rules for contributors and coding agents.

## License

MIT — see [LICENSE](LICENSE).
