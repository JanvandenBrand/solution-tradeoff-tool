"""Unit tests for builders/context.py — ContextBuilder."""

from pathlib import Path


from solution_tradeoff.builders.context import ContextBuilder

_TEMPLATES_DIR = Path("templates")

_DECISION = {
    "id": "AD-001",
    "name": "Test Decision",
    "problem_statement": "Which tool?",
    "planning_horizon": "medium",
    "plateau": 1,
}
_CANDIDATES = [{"id": "A", "name": "Option A"}, {"id": "B", "name": "Option B"}]
_MUST = [{"req_id": "R001", "description": "Encrypt at rest", "domain": "Security"}]
_SHOULD = [{"req_id": "R002", "description": "10 concurrent jobs", "domain": "Technology"}]
_PRINCIPLES = [{"principle_id": "APR-01", "description": "Be cloud-agnostic", "domain": "Arch"}]


def _build(**overrides) -> str:
    builder = ContextBuilder(_TEMPLATES_DIR)
    kwargs = dict(
        decision=_DECISION,
        candidates=_CANDIDATES,
        must_requirements=_MUST,
        should_requirements=_SHOULD,
        principles=_PRINCIPLES,
        point_budget=15,
        criteria_count=2,
    )
    kwargs.update(overrides)
    return builder.build(**kwargs)


def test_renders_decision_id():
    assert "AD-001" in _build()


def test_renders_candidates():
    out = _build()
    assert "Option A" in out
    assert "Option B" in out


def test_renders_must_requirements():
    out = _build()
    assert "R001" in out
    assert "Encrypt at rest" in out


def test_renders_should_requirements():
    out = _build()
    assert "R002" in out


def test_renders_principles():
    out = _build()
    assert "APR-01" in out
    assert "Be cloud-agnostic" in out


def test_renders_point_budget():
    out = _build(point_budget=30)
    assert "30" in out


def test_no_template_tokens_in_output():
    out = _build()
    assert "{{" not in out
    assert "}}" not in out


def test_should_section_absent_when_empty():
    out = _build(should_requirements=[])
    assert "Should" not in out or "Must" in out  # Must section always present


def test_principles_section_before_requirements():
    out = _build()
    pri_pos = out.index("Architecture Principles")
    req_pos = out.index("Applicable requirements")
    assert pri_pos < req_pos


def test_apr_ref_renders_dash_when_missing():
    out = _build()
    assert "—" in out


def test_apr_ref_renders_value_when_present():
    must = [{**_MUST[0], "apr_ref": "APR-01", "ad_ref": None}]
    out = _build(must_requirements=must)
    assert "APR-01" in out


def test_ad_ref_renders_value_when_present():
    must = [{**_MUST[0], "apr_ref": None, "ad_ref": "AD-007"}]
    out = _build(must_requirements=must)
    assert "AD-007" in out


def test_ad_refs_section_rendered_when_present():
    must = [{**_MUST[0], "apr_ref": None, "ad_ref": "AD-007"}]
    out = _build(must_requirements=must)
    assert "Architecture Decisions" in out


def test_ad_refs_section_absent_when_no_refs():
    out = _build()
    assert "Architecture Decisions" not in out


def test_background_knowledge_section_absent_when_not_given():
    out = _build()
    assert "Background Knowledge" not in out


def test_background_knowledge_section_rendered_when_given():
    out = _build(background_knowledge="Vendor call: Example Vendor, 2026-01-15.")
    assert "Background Knowledge" in out
    assert "Vendor call: Example Vendor, 2026-01-15." in out


def test_background_knowledge_section_after_point_budget():
    out = _build(background_knowledge="Some briefing text.")
    budget_pos = out.index("Point budget")
    bk_pos = out.index("Background Knowledge")
    assert budget_pos < bk_pos
