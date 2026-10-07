"""solution-tradeoff CLI — thin facade over the application modules."""

import dataclasses
import hashlib
import json
import re
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from solution_tradeoff.builders.agent_prompt import AgentPromptBuilder
from solution_tradeoff.builders.context import ContextBuilder
from solution_tradeoff.loaders.config import ConfigLoader, DecisionLoader
from solution_tradeoff.loaders.requirements import RequirementsLoader
from solution_tradeoff.pipeline.moscow_filter import MoSCoWFilter
from solution_tradeoff.pipeline.weighter import PerspectiveWeighter
from solution_tradeoff.preflight.checker import PrefightChecker
from solution_tradeoff.preflight.perspectives import verify_perspective as _verify_perspective
from solution_tradeoff.renderers.file_renderer import FileRenderer
from solution_tradeoff.runners.api_runner import DEFAULT_MODEL, ApiRunner, extract_yaml
from solution_tradeoff.validators.schema_validator import SchemaValidator

_PERSPECTIVES_DIR = Path("perspectives")
_DECISION_PATH = Path("decision.yaml")

_console = Console()


@click.group()
def app() -> None:
    """Multi-stakeholder solution trade-off tool."""


@app.command("validate-config")
@click.option(
    "--decision",
    "decision_path",
    default=str(_DECISION_PATH),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to decision.yaml",
)
@click.option(
    "--perspectives-dir",
    "perspectives_dir",
    default=str(_PERSPECTIVES_DIR),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to perspectives/ directory",
)
def validate_config(decision_path: Path, perspectives_dir: Path) -> None:
    """Run all pre-flight checks and report the result."""
    checker = PrefightChecker(perspectives_dir)

    # Load perspectives to show a summary before the gate
    loader = ConfigLoader(perspectives_dir)
    try:
        all_perspectives = loader.load_all()
    except ValueError as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    try:
        decision = DecisionLoader(perspectives_dir).load(decision_path)
    except (FileNotFoundError, ValueError) as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    _console.print(
        f"[green]✓[/green] perspectives/ directory found ({len(all_perspectives)} files)"
    )
    _console.print(
        f"[green]✓[/green] decision.yaml valid "
        f"({decision.id}, {len(decision.candidates)} candidates, "
        f"{len(decision.perspectives)} perspectives selected)"
    )

    checker.run(decision_path)

    _console.print("[green]✓[/green] All checks passed. Build is ready to start.")


@app.command("verify-perspective")
@click.option("--id", "perspective_id", required=True, help="Perspective id to verify")
@click.option(
    "--perspectives-dir",
    "perspectives_dir",
    default=str(_PERSPECTIVES_DIR),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to perspectives/ directory",
)
def verify_perspective_cmd(perspective_id: str, perspectives_dir: Path) -> None:
    """Interactively verify a perspective and write the result to its YAML file."""
    _verify_perspective(perspective_id, perspectives_dir)


@app.command("list-perspectives")
@click.option(
    "--perspectives-dir",
    "perspectives_dir",
    default=str(_PERSPECTIVES_DIR),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to perspectives/ directory",
)
def list_perspectives(perspectives_dir: Path) -> None:
    """List all perspectives with their index, label, and verification status."""
    loader = ConfigLoader(perspectives_dir)
    try:
        perspectives = loader.load_all()
    except ValueError as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    table = Table(title="Perspectives")
    table.add_column("Index", style="dim", width=6)
    table.add_column("ID")
    table.add_column("Label")
    table.add_column("Verified", justify="center")

    for p in perspectives:
        status = "[green]✓[/green]" if p.verified else "[red]✗[/red]"
        table.add_row(str(p.index), p.id, p.label, status)

    _console.print(table)


_CONFIG_PATH = Path("config.yaml")
_TEMPLATES_DIR = Path("templates")
_OUTPUT_ROOT = Path("outputs")


@app.command("build-prompts")
@click.option(
    "--decision",
    "decision_path",
    default=str(_DECISION_PATH),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to decision.yaml",
)
@click.option(
    "--xlsx",
    "xlsx_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Path to requirements xlsx file",
)
@click.option(
    "--config",
    "config_path",
    default=str(_CONFIG_PATH),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to config.yaml",
)
@click.option(
    "--output",
    "output_root",
    default=str(_OUTPUT_ROOT),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Output directory root",
)
@click.option(
    "--perspectives-dir",
    "perspectives_dir",
    default=str(_PERSPECTIVES_DIR),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to perspectives/ directory",
)
@click.option(
    "--dry-run", "dry_run", is_flag=True, help="Validate and summarise; do not write files"
)
@click.option("--force", "force", is_flag=True, help="Overwrite existing output directory")
def build_prompts(
    decision_path: Path,
    xlsx_path: Path,
    config_path: Path,
    output_root: Path,
    perspectives_dir: Path,
    dry_run: bool,
    force: bool,
) -> None:
    """Build the full prompt package from decision.yaml and requirements xlsx."""
    # Pre-flight gate — sacred, always runs first
    from solution_tradeoff.preflight.checker import PrefightChecker

    PrefightChecker(perspectives_dir).run(decision_path, xlsx_path)

    # Load config
    try:
        with open(config_path) as fh:
            cfg = yaml.safe_load(fh)
    except FileNotFoundError:
        _console.print(f"[red]✗[/red] config.yaml not found: {config_path}")
        sys.exit(1)

    # Load and validate decision
    try:
        decision = DecisionLoader(perspectives_dir).load(decision_path)
    except (FileNotFoundError, ValueError) as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    # Convert to raw dicts for template rendering (matching original script format)
    dec_dict = {
        "id": decision.id,
        "name": decision.name,
        "problem_statement": decision.problem_statement,
        "planning_horizon": decision.planning_horizon,
        "plateau": decision.plateau,
    }
    candidates_list = [{"id": c.id, "name": c.name} for c in decision.candidates]

    # Load xlsx
    try:
        req_rows, principles = RequirementsLoader(cfg).load(xlsx_path)
    except (FileNotFoundError, ValueError) as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    # Filter requirements
    must_reqs, should_reqs = MoSCoWFilter().run(
        req_rows, decision.requirements_filter, decision.plateau
    )

    criteria_count = len(must_reqs) + len(should_reqs)
    point_budget = PerspectiveWeighter(cfg).calculate(criteria_count)

    # Load perspectives as dicts for template compatibility
    loader = ConfigLoader(perspectives_dir)
    perspective_objects = []
    for pid in decision.perspectives:
        try:
            p = loader.load_one(pid)
        except ValueError as exc:
            _console.print(f"[red]✗[/red] {exc}")
            sys.exit(1)
        perspective_objects.append(dataclasses.asdict(p))
    perspective_objects.sort(key=lambda p: p["index"])

    _console.print(f"[green]✓[/green] Decision {decision.id} loaded")
    _console.print(
        f"[green]✓[/green] {criteria_count} requirements filtered "
        f"({len(must_reqs)} Must, {len(should_reqs)} Should)"
    )
    _console.print(f"[green]✓[/green] {len(principles)} principles filtered")
    _console.print(
        f"[green]✓[/green] {len(perspective_objects)} perspective agents prepared "
        f"(point budget: {point_budget})"
    )

    if dry_run:
        _console.print("  \\[dry-run] No files written.")
        return

    background_knowledge = None
    if decision.background_knowledge_path:
        bk_path = decision_path.parent / decision.background_knowledge_path
        background_knowledge = bk_path.read_text(encoding="utf-8")

    context_block = ContextBuilder(_TEMPLATES_DIR).build(
        decision=dec_dict,
        candidates=candidates_list,
        must_requirements=must_reqs,
        should_requirements=should_reqs,
        principles=principles,
        point_budget=point_budget,
        criteria_count=criteria_count,
        architecture_decisions=decision.architecture_decisions,
        background_knowledge=background_knowledge,
    )

    prompt_builder = AgentPromptBuilder(_TEMPLATES_DIR)
    perspective_prompts = [
        (p, prompt_builder.build_perspective(context_block, p, point_budget))
        for p in perspective_objects
    ]
    synthesis_prompt = prompt_builder.build_synthesis(perspective_objects)
    compile_prompt = prompt_builder.build_compile(dec_dict, candidates_list, perspective_objects)

    out_dir = FileRenderer(output_root, cfg).write(
        decision_id=decision.id,
        decision_name=decision.name,
        candidates=candidates_list,
        context_block=context_block,
        perspective_prompts=perspective_prompts,
        synthesis_prompt=synthesis_prompt,
        compile_prompt=compile_prompt,
        must_reqs=must_reqs,
        should_reqs=should_reqs,
        principles=principles,
        perspective_objects=perspective_objects,
        point_budget=point_budget,
        criteria_count=criteria_count,
        force=force,
        problem_statement=decision.problem_statement,
        planning_horizon=decision.planning_horizon,
        plateau=decision.plateau,
    )

    out_cfg = cfg["output"]
    _console.print(f"[green]✓[/green] Output written to {out_dir}/")
    _console.print(f"  → Review:   {out_dir}/{out_cfg['review_filename']}")
    _console.print(f"  → Manifest: {out_dir}/{out_cfg['manifest_filename']}")
    _console.print(f"  → Compile:  {out_dir}/{out_cfg['compile_filename']}")


_SCHEMA_PATH = Path("schemas/tradeoff-output.schema.json")
_RESPONSES_DIR = Path("responses")


@app.command("validate-yaml")
@click.option(
    "--responses-dir",
    "responses_dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory containing perspective agent YAML response files",
)
@click.option(
    "--schema",
    "schema_path",
    default=str(_SCHEMA_PATH),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to the JSON Schema file",
)
def validate_yaml(responses_dir: Path, schema_path: Path) -> None:
    """Validate perspective agent YAML response files against the trade-off schema."""
    try:
        validator = SchemaValidator(schema_path)
    except FileNotFoundError as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    try:
        results = validator.validate_directory(responses_dir)
    except FileNotFoundError as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    if not results:
        _console.print(f"[yellow]⚠[/yellow] No .yaml files found in {responses_dir}")
        return

    all_valid = True
    for path, errors in results.items():
        if errors:
            all_valid = False
            _console.print(f"[red]✗[/red] {path.name} — {len(errors)} error(s):")
            for err in errors:
                _console.print(f"     {err.message}")
        else:
            _console.print(f"[green]✓[/green] {path.name}")

    # Duplicate detection: hash canonical JSON of each valid file's parsed content.
    fingerprints: dict[str, list[Path]] = {}
    for path, errors in results.items():
        if not errors:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            key = hashlib.sha256(
                json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            fingerprints.setdefault(key, []).append(path)

    duplicates = {k: v for k, v in fingerprints.items() if len(v) > 1}
    if duplicates:
        all_valid = False
        _console.print(
            "\n[yellow]⚠[/yellow] Duplicate responses detected (likely copy-paste error):"
        )
        for paths in duplicates.values():
            names = " == ".join(p.name for p in paths)
            _console.print(f"     {names}")

    if all_valid:
        _console.print(f"\n[green]✓[/green] All {len(results)} file(s) valid.")
    else:
        n_invalid = sum(1 for e in results.values() if e)
        if n_invalid:
            _console.print(f"\n[red]{n_invalid}/{len(results)} file(s) invalid.[/red]")
        sys.exit(1)


def _select_perspective_files(
    perspective_files: list[Path], perspective_ids: tuple[str, ...]
) -> list[Path]:
    """Filter agent files down to the requested perspective ids, preserving file order.

    Args:
        perspective_files: All perspective agent files found in agents/, sorted.
        perspective_ids: Perspective ids to keep (empty = keep all).

    Returns:
        The filtered list, in the original file order.

    Raises:
        ValueError: If any requested id has no matching file. Lists every unknown
            id and every available id in a single message (fail clearly, in one pass).
    """
    if not perspective_ids:
        return perspective_files

    available = {pf.stem.split("_", 1)[1]: pf for pf in perspective_files}
    unknown = [pid for pid in perspective_ids if pid not in available]
    if unknown:
        raise ValueError(
            f"Unknown perspective id(s): {', '.join(unknown)}. "
            f"Available: {', '.join(sorted(available))}"
        )

    wanted = set(perspective_ids)
    return [pf for pf in perspective_files if pf.stem.split("_", 1)[1] in wanted]


@app.command("run-perspectives")
@click.option(
    "--output-dir",
    "output_dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory produced by build-prompts (contains agents/ subdirectory)",
)
@click.option(
    "--responses-dir",
    "responses_dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory where YAML responses will be saved",
)
@click.option(
    "--schema",
    "schema_path",
    default=str(_SCHEMA_PATH),
    show_default=True,
    type=click.Path(path_type=Path),
    help="Path to the JSON Schema file",
)
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Claude model ID")
@click.option(
    "--perspective",
    "perspective_ids",
    multiple=True,
    help="Perspective id to run (repeatable). Default: all perspectives in agents/.",
)
def run_perspectives(
    output_dir: Path,
    responses_dir: Path,
    schema_path: Path,
    model: str,
    perspective_ids: tuple[str, ...],
) -> None:
    """Call the Claude API for each perspective prompt and save validated YAML responses."""
    agents_dir = output_dir / "agents"
    context_file = agents_dir / "00_context.md"

    if not context_file.exists():
        _console.print(f"[red]✗[/red] Context file not found: {context_file}")
        sys.exit(1)

    system_prompt = context_file.read_text(encoding="utf-8")

    perspective_files = sorted(
        [
            f
            for f in agents_dir.glob("*.md")
            if f.name != "00_context.md" and not f.stem.endswith("_synthesis")
        ]
    )

    if not perspective_files:
        _console.print(f"[yellow]⚠[/yellow] No perspective files found in {agents_dir}")
        return

    try:
        perspective_files = _select_perspective_files(perspective_files, perspective_ids)
    except ValueError as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    responses_dir.mkdir(parents=True, exist_ok=True)

    try:
        runner = ApiRunner(model)
    except EnvironmentError as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    try:
        validator = SchemaValidator(schema_path)
    except FileNotFoundError as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    invalid_count = 0
    for pf in perspective_files:
        perspective_id = pf.stem.split("_", 1)[1]
        prompt = pf.read_text(encoding="utf-8")

        _console.print(f"  {pf.name} ...", end=" ")
        response = runner.send(user=prompt, system=system_prompt)
        yaml_text = extract_yaml(response)

        out_path = responses_dir / f"{perspective_id}.yaml"
        out_path.write_text(yaml_text, encoding="utf-8")

        errors = validator.validate_file(out_path)
        if errors:
            invalid_count += 1
            _console.print(f"[red]✗[/red] {len(errors)} error(s):")
            for err in errors:
                _console.print(f"     {err.message}")
        else:
            _console.print("[green]✓[/green]")

    total = len(perspective_files)
    if invalid_count == 0:
        _console.print(
            f"\n[green]✓[/green] All {total} response(s) valid. "
            f"Responses saved to {responses_dir}/"
        )
    else:
        _console.print(
            f"\n[yellow]⚠[/yellow] {invalid_count}/{total} response(s) invalid — "
            f"review files in {responses_dir}/ and re-run those sessions."
        )


@app.command("run-compile")
@click.option(
    "--output-dir",
    "output_dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory produced by build-prompts (contains compile-prompt.md)",
)
@click.option(
    "--responses-dir",
    "responses_dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory containing validated YAML response files",
)
@click.option(
    "--output",
    "analysis_path",
    default=None,
    type=click.Path(path_type=Path),
    help="Path for the analysis output (default: <output-dir>/analysis.md)",
)
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Claude model ID")
def run_compile(
    output_dir: Path,
    responses_dir: Path,
    analysis_path: Path | None,
    model: str,
) -> None:
    """Embed validated YAML responses into the compile prompt and call the Claude API."""
    compile_prompt_path = output_dir / "compile-prompt.md"
    if not compile_prompt_path.exists():
        _console.print(f"[red]✗[/red] Compile prompt not found: {compile_prompt_path}")
        _console.print("  → Run build-prompts first to generate it.")
        sys.exit(1)

    if not responses_dir.exists():
        _console.print(f"[red]✗[/red] Responses directory not found: {responses_dir}")
        sys.exit(1)

    compile_prompt = compile_prompt_path.read_text(encoding="utf-8")

    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        placeholder_id = match.group(1).lower()
        yaml_file = responses_dir / f"{placeholder_id}.yaml"
        if yaml_file.exists():
            return yaml_file.read_text(encoding="utf-8")
        missing.append(placeholder_id)
        return match.group(0)

    filled_prompt = re.sub(r"\[PASTE ([A-Z_]+) YAML HERE\]", _replace, compile_prompt)

    if missing:
        _console.print(
            f"[yellow]⚠[/yellow] No YAML found for: {', '.join(missing)} — "
            "placeholders left in prompt."
        )

    try:
        runner = ApiRunner(model)
    except EnvironmentError as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    _console.print("  Calling Claude API for compile step ...", end=" ")
    analysis = runner.send(user=filled_prompt)

    if analysis_path is None:
        analysis_path = output_dir / "analysis.md"

    analysis_path.write_text(analysis, encoding="utf-8")
    _console.print("[green]✓[/green]")
    _console.print(f"[green]✓[/green] Analysis written to {analysis_path}")
