"""verify-perspective: interactive command that marks a perspective as verified.

Only this module may write the verified/verified_by/verified_at fields.
"""

import sys
from datetime import date
from pathlib import Path

import yaml
from rich.console import Console
from rich.prompt import Confirm, Prompt

from solution_tradeoff.loaders.config import ConfigLoader

_console = Console()


def verify_perspective(perspective_id: str, perspectives_dir: Path) -> None:
    """Interactively verify a perspective and write the result back to its YAML file.

    Reads the perspective file, displays the full schema for review, prompts
    the user to confirm, then writes verified=true/verified_by/verified_at.

    If the user declines, the file is NOT modified.

    Args:
        perspective_id: The kebab-case id (= stem of the YAML filename).
        perspectives_dir: Directory containing perspective YAML files.
    """
    loader = ConfigLoader(perspectives_dir)
    try:
        perspective = loader.load_one(perspective_id)
    except ValueError as exc:
        _console.print(f"[red]✗[/red] {exc}")
        sys.exit(1)

    _console.print(f"\n[bold]Perspective: {perspective.id}[/bold] — {perspective.label}")
    _console.print(f"  Index : {perspective.index}")
    _console.print(f"\n[bold]Role[/bold]\n{perspective.role.strip()}")
    _console.print(f"\n[bold]Primary concern[/bold]\n{perspective.primary_concern.strip()}")
    _console.print(f"\n[bold]Failure mode[/bold]\n{perspective.failure_mode.strip()}")
    _console.print("\n[bold]Evaluation lens[/bold]")
    for lens in perspective.evaluation_lens:
        _console.print(f"  • {lens}")

    if perspective.verified:
        _console.print(
            f"\n[yellow]Already verified[/yellow] by {perspective.verified_by} "
            f"on {perspective.verified_at}."
        )

    confirmed = Confirm.ask(f"\nMark [bold]{perspective_id}[/bold] as verified?", default=False)
    if not confirmed:
        _console.print("[yellow]Aborted. File not modified.[/yellow]")
        return

    verifier = Prompt.ask("Your name (verified_by)")
    if not verifier.strip():
        _console.print("[red]✗[/red] Name cannot be empty. File not modified.")
        sys.exit(1)

    today = date.today()

    path = perspectives_dir / f"{perspective_id}.yaml"
    with open(path) as fh:
        raw = yaml.safe_load(fh)

    raw["verified"] = True
    raw["verified_by"] = verifier.strip()
    raw["verified_at"] = today

    with open(path, "w") as fh:
        yaml.dump(raw, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)

    _console.print(f"[green]✓[/green] {perspective_id} verified by {verifier.strip()} on {today}.")
