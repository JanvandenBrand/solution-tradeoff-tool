"""Unit tests for pipeline/context.py — PipelineContext."""

from solution_tradeoff.pipeline.context import PipelineContext

_DECISION = {"id": "AD-001", "name": "Test"}
_CANDIDATES = [{"id": "A", "name": "Option A"}]
_MUST = [{"req_id": "R001", "description": "X", "domain": "D", "moscow": "Must"}]
_SHOULD = [{"req_id": "R002", "description": "Y", "domain": "D", "moscow": "Should"}]
_PRINCIPLES = [{"principle_id": "APR-01", "description": "Be cloud-agnostic", "domain": "Arch"}]
_AD_REFS = ["AD-001", "AD-007"]
_PERSPECTIVES = [{"id": "clinical", "label": "Clinical", "index": 1}]


def test_holds_decision():
    ctx = PipelineContext(decision=_DECISION, candidates=_CANDIDATES)
    assert ctx.decision["id"] == "AD-001"


def test_holds_candidates():
    ctx = PipelineContext(decision=_DECISION, candidates=_CANDIDATES)
    assert ctx.candidates[0]["id"] == "A"


def test_holds_must_and_should_reqs():
    ctx = PipelineContext(
        decision=_DECISION, candidates=_CANDIDATES, must_reqs=_MUST, should_reqs=_SHOULD
    )
    assert len(ctx.must_reqs) == 1
    assert len(ctx.should_reqs) == 1


def test_holds_principles():
    ctx = PipelineContext(decision=_DECISION, candidates=_CANDIDATES, principles=_PRINCIPLES)
    assert ctx.principles[0]["principle_id"] == "APR-01"


def test_holds_ad_refs():
    ctx = PipelineContext(decision=_DECISION, candidates=_CANDIDATES, ad_refs=_AD_REFS)
    assert ctx.ad_refs == ["AD-001", "AD-007"]


def test_holds_perspective_objects():
    ctx = PipelineContext(
        decision=_DECISION, candidates=_CANDIDATES, perspective_objects=_PERSPECTIVES
    )
    assert ctx.perspective_objects[0]["id"] == "clinical"


def test_holds_budget_and_criteria():
    ctx = PipelineContext(
        decision=_DECISION, candidates=_CANDIDATES, point_budget=180, criteria_count=73
    )
    assert ctx.point_budget == 180
    assert ctx.criteria_count == 73


def test_defaults_to_empty_lists():
    ctx = PipelineContext(decision=_DECISION, candidates=_CANDIDATES)
    assert ctx.must_reqs == []
    assert ctx.should_reqs == []
    assert ctx.principles == []
    assert ctx.ad_refs == []
    assert ctx.perspective_objects == []
