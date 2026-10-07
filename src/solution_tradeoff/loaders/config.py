"""Config and Decision loaders."""

from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from solution_tradeoff.models.decision import Candidate, Decision
from solution_tradeoff.models.perspective import Perspective

_KNOWN_HORIZONS = {"short", "medium", "long"}
_REQUIRED_PERSPECTIVE_FIELDS = ("id", "label", "index", "role", "primary_concern", "failure_mode")


class ConfigLoader:
    """Loads Perspective objects from the perspectives/ directory."""

    def __init__(self, perspectives_dir: Path) -> None:
        self._dir = perspectives_dir

    def load_all(self) -> list[Perspective]:
        """Return all perspectives in the directory, sorted by index.

        Raises:
            ValueError: If the directory is missing or empty, or any file is invalid.
        """
        if not self._dir.exists():
            raise ValueError(
                f"Perspectives directory not found: {self._dir}\n"
                f"  Create the directory and add at least one .yaml file."
            )
        files = sorted(self._dir.glob("*.yaml"))
        if not files:
            raise ValueError(f"Perspectives directory '{self._dir}' contains no .yaml files.")
        perspectives = [self.load_one(p.stem) for p in files]
        perspectives.sort(key=lambda p: p.index)
        return perspectives

    def load_one(self, perspective_id: str) -> Perspective:
        """Load a single perspective by id (stem of the YAML filename).

        Raises:
            ValueError: If the file is missing or any required field is absent.
        """
        path = self._dir / f"{perspective_id}.yaml"
        if not path.exists():
            raise ValueError(
                f"Perspective file not found: {path}\n"
                f"  Expected a file named '{perspective_id}.yaml' in {self._dir}."
            )
        with open(path) as fh:
            try:
                data = yaml.safe_load(fh)
            except yaml.YAMLError as exc:
                raise ValueError(f"Perspective file '{path}' is not valid YAML: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"Perspective file '{path}': expected a YAML mapping, got {type(data).__name__}"
            )

        errors: list[str] = []
        for field in _REQUIRED_PERSPECTIVE_FIELDS:
            if not data.get(field) and data.get(field) != 0:
                errors.append(f"  Missing required field '{field}' in {path}")
        if errors:
            raise ValueError("\n".join(errors))

        verified_at_raw = data.get("verified_at")
        verified_at: Optional[date] = None
        if isinstance(verified_at_raw, date):
            verified_at = verified_at_raw

        return Perspective(
            id=str(data["id"]),
            label=str(data["label"]),
            index=int(data["index"]),
            role=str(data["role"]),
            primary_concern=str(data["primary_concern"]),
            failure_mode=str(data["failure_mode"]),
            evaluation_lens=list(data.get("evaluation_lens") or []),
            verified=bool(data.get("verified", False)),
            verified_by=data.get("verified_by") or None,
            verified_at=verified_at,
        )


class DecisionLoader:
    """Loads a Decision (with Candidates) from a decision.yaml file."""

    def __init__(self, perspectives_dir: Path) -> None:
        self._perspectives_dir = perspectives_dir

    def load(self, decision_path: Path) -> Decision:
        """Load and validate decision.yaml → Decision.

        Raises:
            FileNotFoundError: If decision_path does not exist.
            ValueError: If any required field is missing or invalid.
        """
        if not decision_path.exists():
            raise FileNotFoundError(f"decision.yaml not found: {decision_path}")
        with open(decision_path) as fh:
            try:
                raw = yaml.safe_load(fh)
            except yaml.YAMLError as exc:
                raise ValueError(f"decision.yaml is not valid YAML: {exc}") from exc

        errors: list[str] = []

        dec = raw.get("decision") or {}
        for field in ("id", "name", "problem_statement", "planning_horizon"):
            if not dec.get(field):
                errors.append(f"decision.yaml: missing required field 'decision.{field}'")

        horizon = dec.get("planning_horizon", "")
        if horizon and horizon not in _KNOWN_HORIZONS:
            allowed = sorted(_KNOWN_HORIZONS)
            errors.append(
                f"decision.yaml: 'planning_horizon' must be one of {allowed}, got '{horizon}'"
            )

        raw_candidates = raw.get("candidates") or []
        if len(raw_candidates) < 2:
            errors.append("decision.yaml: 'candidates' requires at least 2 items")
        if len(raw_candidates) > 5:
            errors.append("decision.yaml: 'candidates' allows at most 5 items")

        raw_perspectives = raw.get("perspectives") or []
        if not raw_perspectives:
            errors.append("decision.yaml: 'perspectives' requires at least 1 item")
        else:
            available = {p.stem for p in self._perspectives_dir.glob("*.yaml")}
            unknown = set(raw_perspectives) - available
            if unknown:
                errors.append(
                    f"decision.yaml: unknown perspective(s) {sorted(unknown)}. "
                    f"Allowed: {sorted(available)}"
                )

        if errors:
            raise ValueError("\n".join(errors))

        candidates = [Candidate(id=str(c["id"]), name=str(c["name"])) for c in raw_candidates]

        return Decision(
            id=str(dec["id"]),
            name=str(dec["name"]),
            problem_statement=str(dec["problem_statement"]),
            planning_horizon=str(dec["planning_horizon"]),
            candidates=candidates,
            perspectives=[str(p) for p in raw_perspectives],
            requirements_filter=raw.get("requirements_filter") or {},
            plateau=dec.get("plateau"),
            architecture_decisions=[str(ad) for ad in (raw.get("architecture_decisions") or [])],
            background_knowledge_path=raw.get("background_knowledge_path") or None,
        )
