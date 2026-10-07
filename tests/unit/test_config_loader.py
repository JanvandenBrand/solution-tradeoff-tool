"""Unit tests for loaders/config.py — ConfigLoader and DecisionLoader."""

from datetime import date
from pathlib import Path

import pytest
import yaml

from solution_tradeoff.loaders.config import ConfigLoader, DecisionLoader
from solution_tradeoff.models.decision import Decision
from solution_tradeoff.models.perspective import Perspective

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_PERSPECTIVE = {
    "id": "clinical",
    "label": "Clinical End-User Perspective",
    "index": 1,
    "role": "Ward nurse",
    "primary_concern": "Workflow disruption",
    "failure_mode": "Added documentation burden",
    "evaluation_lens": ["Does this add work?"],
    "verified": False,
    "verified_by": None,
    "verified_at": None,
}

_VERIFIED_PERSPECTIVE = {
    **_MINIMAL_PERSPECTIVE,
    "verified": True,
    "verified_by": "jan",
    "verified_at": date(2026, 5, 19),
}

_MINIMAL_DECISION = {
    "decision": {
        "id": "AD-001",
        "name": "Test Decision",
        "problem_statement": "Which tool?",
        "planning_horizon": "medium",
    },
    "candidates": [
        {"id": "A", "name": "Option A"},
        {"id": "B", "name": "Option B"},
    ],
    "perspectives": ["clinical"],
    "requirements_filter": {"domains": [], "moscow": ["Must", "Should"]},
}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, default_flow_style=False))


def _make_perspective_dir(tmp_path: Path, perspectives: dict[str, dict]) -> Path:
    d = tmp_path / "perspectives"
    d.mkdir()
    for name, data in perspectives.items():
        _write_yaml(d / f"{name}.yaml", data)
    return d


# ---------------------------------------------------------------------------
# ConfigLoader — load_one
# ---------------------------------------------------------------------------


def test_load_one_returns_perspective(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    loader = ConfigLoader(d)
    p = loader.load_one("clinical")
    assert isinstance(p, Perspective)
    assert p.id == "clinical"
    assert p.index == 1
    assert p.verified is False


def test_load_one_missing_file_raises(tmp_path):
    d = _make_perspective_dir(tmp_path, {})
    loader = ConfigLoader(d)
    with pytest.raises(ValueError, match="not found"):
        loader.load_one("clinical")


def test_load_one_missing_required_field_raises(tmp_path):
    bad = {k: v for k, v in _MINIMAL_PERSPECTIVE.items() if k != "role"}
    d = _make_perspective_dir(tmp_path, {"clinical": bad})
    loader = ConfigLoader(d)
    with pytest.raises(ValueError, match="role"):
        loader.load_one("clinical")


def test_load_one_verified_fields_parsed(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _VERIFIED_PERSPECTIVE})
    loader = ConfigLoader(d)
    p = loader.load_one("clinical")
    assert p.verified is True
    assert p.verified_by == "jan"
    assert p.verified_at == date(2026, 5, 19)


def test_load_one_invalid_yaml_raises(tmp_path):
    d = tmp_path / "perspectives"
    d.mkdir()
    (d / "clinical.yaml").write_text("id: [\nbad yaml")
    loader = ConfigLoader(d)
    with pytest.raises(ValueError, match="valid YAML"):
        loader.load_one("clinical")


# ---------------------------------------------------------------------------
# ConfigLoader — load_all
# ---------------------------------------------------------------------------


def test_load_all_returns_sorted_by_index(tmp_path):
    p2 = {**_MINIMAL_PERSPECTIVE, "id": "security", "index": 2}
    p1 = {**_MINIMAL_PERSPECTIVE, "id": "clinical", "index": 1}
    d = _make_perspective_dir(tmp_path, {"security": p2, "clinical": p1})
    loader = ConfigLoader(d)
    result = loader.load_all()
    assert [p.index for p in result] == [1, 2]


def test_load_all_missing_dir_raises(tmp_path):
    loader = ConfigLoader(tmp_path / "nonexistent")
    with pytest.raises(ValueError, match="not found"):
        loader.load_all()


def test_load_all_empty_dir_raises(tmp_path):
    d = tmp_path / "perspectives"
    d.mkdir()
    loader = ConfigLoader(d)
    with pytest.raises(ValueError, match="no .yaml files"):
        loader.load_all()


# ---------------------------------------------------------------------------
# DecisionLoader
# ---------------------------------------------------------------------------


def test_decision_loader_valid(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    dec_path = tmp_path / "decision.yaml"
    _write_yaml(dec_path, _MINIMAL_DECISION)
    loader = DecisionLoader(d)
    result = loader.load(dec_path)
    assert isinstance(result, Decision)
    assert result.id == "AD-001"
    assert len(result.candidates) == 2
    assert result.candidates[0].id == "A"
    assert result.perspectives == ["clinical"]


def test_decision_loader_missing_file_raises(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    loader = DecisionLoader(d)
    with pytest.raises(FileNotFoundError):
        loader.load(tmp_path / "missing.yaml")


def test_decision_loader_missing_name_raises(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    bad = {**_MINIMAL_DECISION, "decision": {**_MINIMAL_DECISION["decision"]}}
    del bad["decision"]["name"]
    dec_path = tmp_path / "decision.yaml"
    _write_yaml(dec_path, bad)
    loader = DecisionLoader(d)
    with pytest.raises(ValueError, match="name"):
        loader.load(dec_path)


def test_decision_loader_invalid_horizon_raises(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    bad = {
        **_MINIMAL_DECISION,
        "decision": {**_MINIMAL_DECISION["decision"], "planning_horizon": "quarterly"},
    }
    dec_path = tmp_path / "decision.yaml"
    _write_yaml(dec_path, bad)
    loader = DecisionLoader(d)
    with pytest.raises(ValueError, match="planning_horizon"):
        loader.load(dec_path)


def test_decision_loader_too_few_candidates_raises(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    bad = {**_MINIMAL_DECISION, "candidates": [{"id": "A", "name": "Only one"}]}
    dec_path = tmp_path / "decision.yaml"
    _write_yaml(dec_path, bad)
    loader = DecisionLoader(d)
    with pytest.raises(ValueError, match="2"):
        loader.load(dec_path)


def test_decision_loader_unknown_perspective_raises(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    bad = {**_MINIMAL_DECISION, "perspectives": ["clinical", "magic_perspective"]}
    dec_path = tmp_path / "decision.yaml"
    _write_yaml(dec_path, bad)
    loader = DecisionLoader(d)
    with pytest.raises(ValueError, match="magic_perspective"):
        loader.load(dec_path)


def test_decision_loader_collects_multiple_errors(tmp_path):
    """Errors for missing name AND invalid horizon reported together."""
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    bad = {
        **_MINIMAL_DECISION,
        "decision": {
            "id": "AD-001",
            "problem_statement": "X",
            "planning_horizon": "quarterly",
            # name is missing
        },
    }
    dec_path = tmp_path / "decision.yaml"
    _write_yaml(dec_path, bad)
    loader = DecisionLoader(d)
    with pytest.raises(ValueError) as exc_info:
        loader.load(dec_path)
    msg = str(exc_info.value)
    assert "name" in msg
    assert "planning_horizon" in msg


def test_decision_loader_plateau_optional(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    dec_path = tmp_path / "decision.yaml"
    _write_yaml(dec_path, _MINIMAL_DECISION)
    loader = DecisionLoader(d)
    result = loader.load(dec_path)
    assert result.plateau is None


def test_decision_loader_background_knowledge_path_optional(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    dec_path = tmp_path / "decision.yaml"
    _write_yaml(dec_path, _MINIMAL_DECISION)
    loader = DecisionLoader(d)
    result = loader.load(dec_path)
    assert result.background_knowledge_path is None


def test_decision_loader_background_knowledge_path_parsed(tmp_path):
    d = _make_perspective_dir(tmp_path, {"clinical": _MINIMAL_PERSPECTIVE})
    dec_path = tmp_path / "decision.yaml"
    data = {**_MINIMAL_DECISION, "background_knowledge_path": "background_knowledge.md"}
    _write_yaml(dec_path, data)
    loader = DecisionLoader(d)
    result = loader.load(dec_path)
    assert result.background_knowledge_path == "background_knowledge.md"
