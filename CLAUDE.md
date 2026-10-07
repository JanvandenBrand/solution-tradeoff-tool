# CLAUDE.md — solution-tradeoff

> Instructions for Claude Code (and other contributors) working on this repository.

---

## Project Purpose

`solution-tradeoff` is a Python CLI tool that generates structured prompt files for
multi-stakeholder solution trade-off analysis. It supports two paths: an automated path
(`run-perspectives`, `run-compile`) that calls the Claude API directly via `ApiRunner`, and a
manual path where the user pastes the generated prompt files into Claude Chat and saves the
responses by hand. Both paths consume the same generated prompt files and validate responses
against the same YAML schema.

---

## Absolute Rules (never violate these)

1. **Always use the virtual environment.** Every command — installs, tests, linting, running the
   CLI — must execute inside the `poetry`-managed venv. Never run `pip install` against the
   system Python.
   ```bash
   pyenv local 3.11.9         # pin Python version for the project directory
   poetry env use python      # create the venv (Poetry 2.x)
   poetry install             # install all dependencies into the venv
   ```

2. **Pre-flight gate is sacred.** No file may be written and no build step may execute before
   `PrefightChecker.run()` has completed without errors. Code that writes output before the
   gate is a bug.

3. **No hardcoding.** Every threshold, ID, budget value, column name, and path must be read from
   config files or injected at the CLI layer.

4. **Never commit decision material.** `outputs/`, `decision.yaml`, `background_knowledge.md`
   and `*.xlsx` (except `examples/`) are git-ignored. They contain real, often confidential,
   decision context. If you accidentally stage them, unstage them before committing.

5. **xlsx is the authoritative requirements source.** Do not add CSV, JSON, or database loaders
   for requirements. If another format is needed, add a converter that produces xlsx.

6. **Fail early, fail clearly.** Pre-flight collects all errors in a single pass, reports all of
   them at once, then calls `sys.exit(1)`. Error messages must name the exact field, file, and
   remediation command.

7. **Perspective verification is explicit.** `verified`, `verified_by` and `verified_at` in
   `perspectives/*.yaml` may only be written by the `verify-perspective` command. Shipped
   perspectives are unverified.

---

## Project Structure

```
solution-tradeoff-tool/
├── config.yaml                  # Column mappings, budget settings, output filenames
├── decision.yaml.example        # Per-analysis config template (copy to decision.yaml)
├── examples/
│   └── requirements_sample.xlsx # Synthetic requirements & principles
├── perspectives/                # One YAML file per stakeholder perspective
├── templates/
│   ├── background_knowledge.md  # Template for the optional per-decision briefing
│   ├── context_block.md.j2      # Shared context → 00_context.md
│   ├── perspective_agent.md.j2  # One prompt per perspective
│   ├── synthesis_agent.md.j2
│   └── compile-prompt.md.j2
├── schemas/
│   └── tradeoff-output.schema.json   # JSON Schema (Draft 2020-12) for agent YAML output
├── src/solution_tradeoff/
│   ├── cli.py                   # Click facade; thin — no business logic
│   ├── preflight/               # PrefightChecker, verify-perspective
│   ├── loaders/                 # RequirementsLoader (xlsx), ConfigLoader, DecisionLoader
│   ├── pipeline/                # PipelineContext, MoSCoWFilter, PerspectiveWeighter
│   ├── builders/                # ContextBuilder, AgentPromptBuilder
│   ├── renderers/               # FileRenderer (prompt files, manifest, review.md)
│   ├── runners/                 # ApiRunner — Claude API calls
│   ├── validators/              # SchemaValidator
│   └── models/                  # Requirement, Perspective, Decision, Candidate
└── tests/
    ├── fixtures/
    ├── unit/
    └── integration/
```

---

## Code Standards

- Type hints and Google-style docstrings (Args / Returns / Raises) on all public interfaces.
- Collect errors, then report them all at once. Never use bare `except`; catch specific
  exceptions (`yaml.YAMLError`, `openpyxl.utils.exceptions.InvalidFileException`, ...).
- `cli.py` is a thin facade: pre-flight first, then load → filter → build → render.
- Inject config and paths through constructors; business logic never opens config files itself.
- All prompt content lives in Jinja2 templates under `templates/`, not in Python strings.
- If you change a public function, class or CLI command, update its docstring and `README.md`
  in the same commit.

## Test Standards

- Every module has a matching test file under `tests/unit/`; CLI flows go in
  `tests/integration/`.
- Test names: `test_{what}`, `test_{what}_when_{condition}`,
  `test_{what}_raises_{exception}_when_{condition}`.
- Fixtures are deterministic: no `random()`, no current time, no paths outside `tmp_path` and
  `tests/fixtures/`.

## Quality Gate

```bash
make check     # flake8, black --check, bandit, mypy, pytest with coverage
```

## Naming Conventions

| Context | Convention | Example |
|---|---|---|
| Python modules, functions, variables | `snake_case` | `moscow_filter.py` |
| Python classes | `PascalCase` | `MoSCoWFilter` |
| CLI commands | `kebab-case` | `build-prompts` |
| Perspective IDs | `snake_case` (match filename) | `data_protection` |
| YAML output field names | `snake_case` | `point_allocations` |

## Out of Scope (do not implement without explicit instruction)

- AI providers other than Anthropic
- Integrations with external services (ticketing, document stores, ...)
- A web UI or REST API
- CSV or database support for requirements
