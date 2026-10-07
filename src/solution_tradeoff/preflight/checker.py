"""PrefightChecker — fail-fast gate that runs before any file is written."""

import sys
from pathlib import Path

from rich.console import Console

from solution_tradeoff.loaders.config import ConfigLoader, DecisionLoader
from solution_tradeoff.models.perspective import Perspective

_console = Console(stderr=True)


class PrefightChecker:
    """Orchestrates all pre-flight checks.

    Collects every error in a single pass, then reports them all and calls
    sys.exit(1).  Never raises on the first error and stops.
    """

    def __init__(self, perspectives_dir: Path) -> None:
        self._perspectives_dir = perspectives_dir

    def run(
        self,
        decision_path: Path,
        xlsx_path: Path | None = None,
    ) -> None:
        """Run all checks.  Exits 1 if any check fails.

        Args:
            decision_path: Path to decision.yaml.
            xlsx_path: Optional path to the requirements xlsx; checked for
                existence when provided.
        """
        errors: list[str] = []

        # ------------------------------------------------------------------
        # Check 1 + 2: perspectives/ directory and each file
        # ------------------------------------------------------------------
        loader = ConfigLoader(self._perspectives_dir)
        all_perspectives: list[Perspective] = []

        if not self._perspectives_dir.exists():
            errors.append(f"Perspectives directory not found: {self._perspectives_dir}")
        else:
            yaml_files = list(self._perspectives_dir.glob("*.yaml"))
            if not yaml_files:
                errors.append(
                    f"Perspectives directory '{self._perspectives_dir}' contains no .yaml files."
                )
            else:
                for yf in sorted(yaml_files):
                    try:
                        all_perspectives.append(loader.load_one(yf.stem))
                    except ValueError as exc:
                        errors.append(str(exc))

        # ------------------------------------------------------------------
        # Check 5: decision.yaml schema
        # ------------------------------------------------------------------
        decision = None
        try:
            decision_loader = DecisionLoader(self._perspectives_dir)
            decision = decision_loader.load(decision_path)
        except FileNotFoundError:
            errors.append(f"decision.yaml not found: {decision_path}")
        except ValueError as exc:
            errors.append(str(exc))

        # ------------------------------------------------------------------
        # Checks 3 + 4: per-perspective existence and verification
        # ------------------------------------------------------------------
        if decision is not None and all_perspectives:
            available_ids = {p.id for p in all_perspectives}
            for pid in decision.perspectives:
                if pid not in available_ids:
                    errors.append(
                        f"Perspective '{pid}' listed in decision.yaml has no "
                        f"matching file in {self._perspectives_dir}.\n"
                        f"  → create {self._perspectives_dir / pid}.yaml"
                    )
                else:
                    match = next(p for p in all_perspectives if p.id == pid)
                    if not match.verified:
                        errors.append(
                            f"Perspective '{pid}' is not yet verified.\n"
                            f"  → run: solution-tradeoff verify-perspective --id {pid}"
                        )

        # ------------------------------------------------------------------
        # Check 6: xlsx exists
        # ------------------------------------------------------------------
        if xlsx_path is not None and not xlsx_path.exists():
            errors.append(f"Requirements file not found: {xlsx_path}")

        # ------------------------------------------------------------------
        # Check 7: background knowledge file exists, if referenced
        # ------------------------------------------------------------------
        if decision is not None and decision.background_knowledge_path:
            bk_path = decision_path.parent / decision.background_knowledge_path
            if not bk_path.exists():
                errors.append(
                    f"Background knowledge file not found: {bk_path}\n"
                    f"  → referenced by decision.yaml 'background_knowledge_path'"
                )

        # ------------------------------------------------------------------
        # Report and exit
        # ------------------------------------------------------------------
        if errors:
            for err in errors:
                _console.print(f"[red]✗[/red] {err}")
            _console.print(
                f"\n[red]{len(errors)} error(s). Build cannot start until all checks pass.[/red]"
            )
            sys.exit(1)
