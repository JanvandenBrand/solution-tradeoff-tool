"""Unit tests for builders/agent_prompt.py — AgentPromptBuilder."""

from pathlib import Path

from solution_tradeoff.builders.agent_prompt import AgentPromptBuilder

_TEMPLATES_DIR = Path("templates")

_PERSPECTIVE = {
    "id": "clinical",
    "label": "Clinical End-User Perspective",
    "index": 1,
    "role": "Ward nurse in an ICU.",
    "primary_concern": "Workflow disruption.",
    "failure_mode": "Added documentation burden.",
    "evaluation_lens": ["Does it add work?", "Were staff consulted?"],
}

_CONTEXT_BLOCK = "## Decision context\n\n- **Decision ID**: AD-001\n"


def _builder() -> AgentPromptBuilder:
    return AgentPromptBuilder(_TEMPLATES_DIR)


# ---------------------------------------------------------------------------
# Perspective prompt
# ---------------------------------------------------------------------------


def test_perspective_contains_role():
    out = _builder().build_perspective(_CONTEXT_BLOCK, _PERSPECTIVE, 15)
    assert "Ward nurse" in out


def test_perspective_contains_point_budget():
    out = _builder().build_perspective(_CONTEXT_BLOCK, _PERSPECTIVE, 30)
    assert "30" in out


def test_perspective_contains_evaluation_lens():
    out = _builder().build_perspective(_CONTEXT_BLOCK, _PERSPECTIVE, 15)
    assert "Does it add work?" in out
    assert "Were staff consulted?" in out


def test_perspective_no_template_tokens():
    out = _builder().build_perspective(_CONTEXT_BLOCK, _PERSPECTIVE, 15)
    assert "{{" not in out
    assert "}}" not in out


# ---------------------------------------------------------------------------
# Synthesis prompt
# ---------------------------------------------------------------------------


def test_synthesis_contains_perspective_label():
    perspectives = [
        _PERSPECTIVE,
        {**_PERSPECTIVE, "id": "security", "label": "Security Perspective"},
    ]
    out = _builder().build_synthesis(perspectives)
    assert "Clinical End-User Perspective" in out
    assert "Security Perspective" in out


def test_synthesis_count_matches():
    perspectives = [_PERSPECTIVE] * 3
    out = _builder().build_synthesis(perspectives)
    assert "3" in out


def test_synthesis_no_template_tokens():
    out = _builder().build_synthesis([_PERSPECTIVE])
    assert "{{" not in out
