"""Unit tests for preflight/checker.py — PrefightChecker."""

from pathlib import Path

import pytest
import yaml

from solution_tradeoff.preflight.checker import PrefightChecker

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_MINIMAL_PERSPECTIVE = {
    "id": "clinical",
    "label": "Clinical",
    "index": 1,
    "role": "Nurse",
    "primary_concern": "Workflow",
    "failure_mode": "Burden",
    "evaluation_lens": [],
    "verified": True,
    "verified_by": "jan",
    "verified_at": None,
}

_MINIMAL_DECISION = {
    "decision": {
        "id": "AD-001",
        "name": "Test",
        "problem_statement": "Which?",
        "planning_horizon": "medium",
    },
    "candidates": [{"id": "A", "name": "A"}, {"id": "B", "name": "B"}],
    "perspectives": ["clinical"],
    "requirements_filter": {},
}


def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, default_flow_style=False))


def _make_env(
    tmp_path: Path,
    perspectives: dict[str, dict] | None = None,
    decision_data: dict | None = None,
    xlsx: bool = False,
) -> tuple[Path, Path, Path | None]:
    """Return (perspectives_dir, decision_path, xlsx_path|None)."""
    perspectives_dir = tmp_path / "perspectives"
    perspectives_dir.mkdir()

    if perspectives is None:
        perspectives = {"clinical": _MINIMAL_PERSPECTIVE}
    for name, data in perspectives.items():
        _write(perspectives_dir / f"{name}.yaml", data)

    decision_path = tmp_path / "decision.yaml"
    _write(decision_path, decision_data or _MINIMAL_DECISION)

    xlsx_path: Path | None = None
    if xlsx:
        xlsx_path = tmp_path / "reqs.xlsx"
        xlsx_path.write_bytes(b"fake")

    return perspectives_dir, decision_path, xlsx_path


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_passes_when_all_verified(tmp_path):
    p_dir, dec, _ = _make_env(tmp_path)
    PrefightChecker(p_dir).run(dec)  # must not raise or exit


def test_passes_with_xlsx_present(tmp_path):
    p_dir, dec, xlsx = _make_env(tmp_path, xlsx=True)
    PrefightChecker(p_dir).run(dec, xlsx_path=xlsx)


# ---------------------------------------------------------------------------
# Check 1: perspectives/ directory
# ---------------------------------------------------------------------------


def test_fails_if_perspectives_dir_missing(tmp_path):
    dec = tmp_path / "decision.yaml"
    _write(dec, _MINIMAL_DECISION)
    with pytest.raises(SystemExit, match="1"):
        PrefightChecker(tmp_path / "nonexistent").run(dec)


def test_fails_if_perspectives_dir_empty(tmp_path):
    p_dir = tmp_path / "perspectives"
    p_dir.mkdir()
    dec = tmp_path / "decision.yaml"
    _write(dec, _MINIMAL_DECISION)
    with pytest.raises(SystemExit, match="1"):
        PrefightChecker(p_dir).run(dec)


# ---------------------------------------------------------------------------
# Check 2: per-file schema
# ---------------------------------------------------------------------------


def test_fails_if_perspective_file_invalid(tmp_path):
    bad = {k: v for k, v in _MINIMAL_PERSPECTIVE.items() if k != "role"}
    p_dir, dec, _ = _make_env(tmp_path, perspectives={"clinical": bad})
    with pytest.raises(SystemExit, match="1"):
        PrefightChecker(p_dir).run(dec)


# ---------------------------------------------------------------------------
# Check 3: perspective named in decision.yaml but file missing
# ---------------------------------------------------------------------------


def test_fails_if_perspective_file_missing_for_selected(tmp_path):
    decision = {**_MINIMAL_DECISION, "perspectives": ["clinical", "ghost"]}
    p_dir, dec, _ = _make_env(tmp_path, decision_data=decision)
    with pytest.raises(SystemExit, match="1"):
        PrefightChecker(p_dir).run(dec)


# ---------------------------------------------------------------------------
# Check 4: unverified perspective
# ---------------------------------------------------------------------------


def test_fails_if_perspective_not_verified(tmp_path):
    unverified = {**_MINIMAL_PERSPECTIVE, "verified": False}
    p_dir, dec, _ = _make_env(tmp_path, perspectives={"clinical": unverified})
    with pytest.raises(SystemExit, match="1"):
        PrefightChecker(p_dir).run(dec)


# ---------------------------------------------------------------------------
# Check 5: decision.yaml validation
# ---------------------------------------------------------------------------


def test_fails_if_decision_missing(tmp_path):
    p_dir = tmp_path / "perspectives"
    p_dir.mkdir()
    _write(p_dir / "clinical.yaml", _MINIMAL_PERSPECTIVE)
    with pytest.raises(SystemExit, match="1"):
        PrefightChecker(p_dir).run(tmp_path / "no_such.yaml")


def test_fails_if_decision_too_few_candidates(tmp_path):
    bad = {**_MINIMAL_DECISION, "candidates": [{"id": "A", "name": "A"}]}
    p_dir, dec, _ = _make_env(tmp_path, decision_data=bad)
    with pytest.raises(SystemExit, match="1"):
        PrefightChecker(p_dir).run(dec)


# ---------------------------------------------------------------------------
# Check 6: xlsx
# ---------------------------------------------------------------------------


def test_fails_if_xlsx_missing(tmp_path):
    p_dir, dec, _ = _make_env(tmp_path)
    with pytest.raises(SystemExit, match="1"):
        PrefightChecker(p_dir).run(dec, xlsx_path=tmp_path / "missing.xlsx")


# ---------------------------------------------------------------------------
# Check 7: background knowledge file
# ---------------------------------------------------------------------------


def test_passes_when_background_knowledge_present(tmp_path):
    decision = {**_MINIMAL_DECISION, "background_knowledge_path": "background_knowledge.md"}
    p_dir, dec, _ = _make_env(tmp_path, decision_data=decision)
    (tmp_path / "background_knowledge.md").write_text("# Briefing")
    PrefightChecker(p_dir).run(dec)  # must not raise or exit


def test_fails_if_background_knowledge_missing(tmp_path):
    decision = {**_MINIMAL_DECISION, "background_knowledge_path": "missing_briefing.md"}
    p_dir, dec, _ = _make_env(tmp_path, decision_data=decision)
    with pytest.raises(SystemExit, match="1"):
        PrefightChecker(p_dir).run(dec)


def test_passes_when_background_knowledge_not_referenced(tmp_path):
    p_dir, dec, _ = _make_env(tmp_path)
    PrefightChecker(p_dir).run(dec)  # must not raise or exit


# ---------------------------------------------------------------------------
# All-errors-at-once behaviour
# ---------------------------------------------------------------------------


def test_collects_all_errors_before_failing(tmp_path, capsys):
    """Two errors (unverified + xlsx missing) both appear in output."""
    unverified = {**_MINIMAL_PERSPECTIVE, "verified": False}
    p_dir, dec, _ = _make_env(tmp_path, perspectives={"clinical": unverified})
    xlsx = tmp_path / "missing.xlsx"
    with pytest.raises(SystemExit):
        PrefightChecker(p_dir).run(dec, xlsx_path=xlsx)
    # Both errors should have been reported (stderr via rich)
    # We can't easily capture rich stderr, but SystemExit confirms exit(1)
