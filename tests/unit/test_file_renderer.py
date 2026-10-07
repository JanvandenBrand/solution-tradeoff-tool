"""Unit tests for renderers/file_renderer.py — FileRenderer."""

import json
from pathlib import Path


from solution_tradeoff.renderers.file_renderer import FileRenderer

_CFG = {
    "output": {
        "agent_filename_pattern": "{index:02d}_{perspective}.md",
        "context_filename": "00_context.md",
        "synthesis_filename": "{N}_synthesis.md",
        "review_filename": "review.md",
        "manifest_filename": "manifest.json",
        "compile_filename": "compile-prompt.md",
    }
}

_PERSPECTIVE = {"id": "clinical", "label": "Clinical", "index": 1}
_CANDIDATES = [{"id": "A", "name": "Option A"}, {"id": "B", "name": "Option B"}]
_MUST = [{"req_id": "R001", "description": "X", "domain": "D", "moscow": "Must"}]
_SHOULD = [{"req_id": "R002", "description": "Y", "domain": "D", "moscow": "Should"}]
_PRINCIPLES = [{"principle_id": "APR-01", "description": "Be cloud-agnostic", "domain": "Arch"}]


def _run(tmp_path: Path) -> Path:
    renderer = FileRenderer(tmp_path / "outputs", _CFG)
    return renderer.write(
        decision_id="AD-001",
        decision_name="Test Decision",
        candidates=_CANDIDATES,
        context_block="# Context\n",
        perspective_prompts=[(_PERSPECTIVE, "# Perspective prompt\n")],
        synthesis_prompt="# Synthesis\n",
        compile_prompt="# Compile\n",
        must_reqs=_MUST,
        should_reqs=_SHOULD,
        principles=_PRINCIPLES,
        perspective_objects=[_PERSPECTIVE],
        point_budget=15,
        criteria_count=2,
    )


# ---------------------------------------------------------------------------
# Directory structure
# ---------------------------------------------------------------------------


def test_output_directory_created(tmp_path):
    out_dir = _run(tmp_path)
    assert out_dir.exists()
    assert (out_dir / "agents").is_dir()


def test_context_file_created(tmp_path):
    out_dir = _run(tmp_path)
    assert (out_dir / "agents" / "00_context.md").exists()


def test_perspective_file_created(tmp_path):
    out_dir = _run(tmp_path)
    assert (out_dir / "agents" / "01_clinical.md").exists()


def test_synthesis_file_created(tmp_path):
    out_dir = _run(tmp_path)
    # 1 perspective + 1 = index 2
    assert (out_dir / "agents" / "02_synthesis.md").exists()


def test_review_file_created(tmp_path):
    out_dir = _run(tmp_path)
    assert (out_dir / "review.md").exists()


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def test_manifest_is_valid_json(tmp_path):
    out_dir = _run(tmp_path)
    data = json.loads((out_dir / "manifest.json").read_text())
    assert data["decision_id"] == "AD-001"


def test_manifest_agent_count(tmp_path):
    out_dir = _run(tmp_path)
    data = json.loads((out_dir / "manifest.json").read_text())
    # context + 1 perspective + synthesis = 3
    assert len(data["agents"]) == 3


def test_manifest_has_timestamp(tmp_path):
    out_dir = _run(tmp_path)
    data = json.loads((out_dir / "manifest.json").read_text())
    assert "generated_at" in data
    assert data["generated_at"]


def test_manifest_counts(tmp_path):
    out_dir = _run(tmp_path)
    data = json.loads((out_dir / "manifest.json").read_text())
    assert data["must_count"] == 1
    assert data["should_count"] == 1
    assert data["criteria_count"] == 2


# ---------------------------------------------------------------------------
# Review checklist
# ---------------------------------------------------------------------------


def test_review_contains_sections(tmp_path):
    out_dir = _run(tmp_path)
    content = (out_dir / "review.md").read_text()
    for section in ["## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "## 7."]:
        assert section in content, f"Missing {section}"


def test_review_contains_decision_id(tmp_path):
    out_dir = _run(tmp_path)
    content = (out_dir / "review.md").read_text()
    assert "AD-001" in content


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_idempotent_second_run_overwrites(tmp_path):
    out_dir = _run(tmp_path)
    data1 = json.loads((out_dir / "manifest.json").read_text())
    _run(tmp_path)
    data2 = json.loads((out_dir / "manifest.json").read_text())
    # Everything except generated_at must be identical
    data1.pop("generated_at")
    data2.pop("generated_at")
    assert data1 == data2
