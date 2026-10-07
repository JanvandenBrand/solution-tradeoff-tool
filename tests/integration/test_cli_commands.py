"""Integration tests for validate-config, list-perspectives, verify-perspective CLI commands."""

from pathlib import Path

import yaml
from click.testing import CliRunner

from solution_tradeoff.cli import app

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_MINIMAL_PERSPECTIVE = {
    "id": "clinical",
    "label": "Clinical",
    "index": 1,
    "role": "Nurse",
    "primary_concern": "Workflow",
    "failure_mode": "Burden",
    "evaluation_lens": ["Does it add work?"],
    "verified": True,
    "verified_by": "jan",
    "verified_at": None,
}

_MINIMAL_DECISION = {
    "decision": {
        "id": "AD-001",
        "name": "Test Decision",
        "problem_statement": "Which tool?",
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
) -> tuple[Path, Path]:
    p_dir = tmp_path / "perspectives"
    p_dir.mkdir()
    for name, data in (perspectives or {"clinical": _MINIMAL_PERSPECTIVE}).items():
        _write(p_dir / f"{name}.yaml", data)
    dec_path = tmp_path / "decision.yaml"
    _write(dec_path, decision_data or _MINIMAL_DECISION)
    return p_dir, dec_path


# ---------------------------------------------------------------------------
# validate-config
# ---------------------------------------------------------------------------


def test_validate_config_happy_path(tmp_path):
    p_dir, dec_path = _make_env(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "validate-config",
            "--decision",
            str(dec_path),
            "--perspectives-dir",
            str(p_dir),
        ],
    )
    assert result.exit_code == 0
    assert "All checks passed" in result.output


def test_validate_config_fails_on_unverified(tmp_path):
    unverified = {**_MINIMAL_PERSPECTIVE, "verified": False}
    p_dir, dec_path = _make_env(tmp_path, perspectives={"clinical": unverified})
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "validate-config",
            "--decision",
            str(dec_path),
            "--perspectives-dir",
            str(p_dir),
        ],
    )
    assert result.exit_code == 1
    assert "verify-perspective" in result.output


def test_validate_config_fails_on_missing_decision(tmp_path):
    p_dir, _ = _make_env(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "validate-config",
            "--decision",
            str(tmp_path / "missing.yaml"),
            "--perspectives-dir",
            str(p_dir),
        ],
    )
    assert result.exit_code == 1


def test_validate_config_shows_summary(tmp_path):
    p_dir, dec_path = _make_env(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "validate-config",
            "--decision",
            str(dec_path),
            "--perspectives-dir",
            str(p_dir),
        ],
    )
    assert "AD-001" in result.output
    assert "perspectives/ directory found" in result.output


# ---------------------------------------------------------------------------
# list-perspectives
# ---------------------------------------------------------------------------


def test_list_perspectives_shows_all(tmp_path):
    p2 = {**_MINIMAL_PERSPECTIVE, "id": "security", "index": 2, "label": "Security Perspective"}
    p_dir, _ = _make_env(tmp_path, perspectives={"clinical": _MINIMAL_PERSPECTIVE, "security": p2})
    runner = CliRunner()
    result = runner.invoke(app, ["list-perspectives", "--perspectives-dir", str(p_dir)])
    assert result.exit_code == 0
    assert "clinical" in result.output
    assert "security" in result.output


def test_list_perspectives_shows_verified_status(tmp_path):
    p_dir, _ = _make_env(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["list-perspectives", "--perspectives-dir", str(p_dir)])
    assert result.exit_code == 0
    assert "✓" in result.output


def test_list_perspectives_fails_on_missing_dir(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["list-perspectives", "--perspectives-dir", str(tmp_path / "nope")])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# verify-perspective (non-interactive path tested via preflight/perspectives.py)
# ---------------------------------------------------------------------------


def test_verify_perspective_writes_verified_fields(tmp_path):
    unverified = {
        **_MINIMAL_PERSPECTIVE,
        "verified": False,
        "verified_by": None,
        "verified_at": None,
    }
    p_dir, _ = _make_env(tmp_path, perspectives={"clinical": unverified})
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["verify-perspective", "--id", "clinical", "--perspectives-dir", str(p_dir)],
        input="y\njan\n",
    )
    assert result.exit_code == 0
    updated = yaml.safe_load((p_dir / "clinical.yaml").read_text())
    assert updated["verified"] is True
    assert updated["verified_by"] == "jan"
    assert updated["verified_at"] is not None


def test_verify_perspective_no_modification_when_declined(tmp_path):
    unverified = {
        **_MINIMAL_PERSPECTIVE,
        "verified": False,
        "verified_by": None,
        "verified_at": None,
    }
    p_dir, _ = _make_env(tmp_path, perspectives={"clinical": unverified})
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["verify-perspective", "--id", "clinical", "--perspectives-dir", str(p_dir)],
        input="n\n",
    )
    assert result.exit_code == 0
    updated = yaml.safe_load((p_dir / "clinical.yaml").read_text())
    assert updated["verified"] is False


def test_verify_perspective_unknown_id_exits_1(tmp_path):
    p_dir, _ = _make_env(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["verify-perspective", "--id", "ghost", "--perspectives-dir", str(p_dir)],
    )
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# validate-yaml — duplicate detection
# ---------------------------------------------------------------------------

_SCHEMA = Path("schemas/tradeoff-output.schema.json")
_VALID_FIXTURE = Path("tests/fixtures/response_valid.yaml")


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, default_flow_style=False))


_VALID_RESPONSE = {
    "perspective_id": "security",
    "concerns": [{"concern": "X", "risk": "Y"}],
    "point_allocations": [{"criterion_id": "REQ001", "points": 10, "rationale": "Z"}],
    "preferred_option": "A",
}


def test_validate_yaml_no_duplicates_exits_0(tmp_path):
    import shutil

    shutil.copy(_VALID_FIXTURE, tmp_path / "security.yaml")
    _write_yaml(
        tmp_path / "architecture.yaml", {**_VALID_RESPONSE, "perspective_id": "architecture"}
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["validate-yaml", "--responses-dir", str(tmp_path), "--schema", str(_SCHEMA)],
    )
    assert result.exit_code == 0
    assert "Duplicate" not in result.output


def test_validate_yaml_duplicate_exits_1(tmp_path):
    import shutil

    shutil.copy(_VALID_FIXTURE, tmp_path / "security.yaml")
    shutil.copy(_VALID_FIXTURE, tmp_path / "architecture.yaml")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["validate-yaml", "--responses-dir", str(tmp_path), "--schema", str(_SCHEMA)],
    )
    assert result.exit_code == 1
    assert "Duplicate" in result.output
    assert "security.yaml" in result.output
    assert "architecture.yaml" in result.output


def test_validate_yaml_duplicate_message_shows_both_files(tmp_path):
    import shutil

    shutil.copy(_VALID_FIXTURE, tmp_path / "alpha.yaml")
    shutil.copy(_VALID_FIXTURE, tmp_path / "beta.yaml")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["validate-yaml", "--responses-dir", str(tmp_path), "--schema", str(_SCHEMA)],
    )
    assert "alpha.yaml" in result.output
    assert "beta.yaml" in result.output


def test_validate_yaml_invalid_plus_duplicate(tmp_path):
    """Invalid files are excluded from duplicate check — only valid files compared."""
    import shutil

    shutil.copy(_VALID_FIXTURE, tmp_path / "security.yaml")
    shutil.copy(_VALID_FIXTURE, tmp_path / "architecture.yaml")
    # Add a structurally invalid file (missing required fields) — should NOT trigger duplicate
    _write_yaml(tmp_path / "broken.yaml", {"perspective_id": "broken"})
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["validate-yaml", "--responses-dir", str(tmp_path), "--schema", str(_SCHEMA)],
    )
    assert result.exit_code == 1
    assert "Duplicate" in result.output
