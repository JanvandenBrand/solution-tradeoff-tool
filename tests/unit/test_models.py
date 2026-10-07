"""Unit tests for models/requirement.py, models/perspective.py, models/decision.py."""

from datetime import date


from solution_tradeoff.models.decision import Candidate, Decision
from solution_tradeoff.models.perspective import Perspective
from solution_tradeoff.models.requirement import Requirement


# ---------------------------------------------------------------------------
# Requirement
# ---------------------------------------------------------------------------


def test_requirement_required_fields():
    r = Requirement(
        req_id="R001",
        description="Store patient data",
        domain="Security",
        moscow="Must",
        status="Active",
    )
    assert r.req_id == "R001"
    assert r.moscow == "Must"


def test_requirement_optional_fields_default_none():
    r = Requirement(req_id="R001", description="X", domain="D", moscow="Must", status="Active")
    assert r.plateau is None
    assert r.apr_ref is None
    assert r.ad_ref is None


def test_requirement_optional_fields_accept_values():
    r = Requirement(
        req_id="R001",
        description="X",
        domain="D",
        moscow="Must",
        status="Active",
        plateau=2,
        apr_ref="APR-01",
        ad_ref="AD-069",
    )
    assert r.plateau == 2
    assert r.apr_ref == "APR-01"
    assert r.ad_ref == "AD-069"


# ---------------------------------------------------------------------------
# Perspective
# ---------------------------------------------------------------------------


def test_perspective_required_fields():
    p = Perspective(
        id="clinical",
        label="Clinical End-User Perspective",
        index=1,
        role="Ward nurse",
        primary_concern="Workflow disruption",
        failure_mode="Added documentation burden",
    )
    assert p.id == "clinical"
    assert p.index == 1


def test_perspective_verified_defaults_false():
    p = Perspective(
        id="clinical",
        label="L",
        index=1,
        role="R",
        primary_concern="PC",
        failure_mode="FM",
    )
    assert p.verified is False
    assert p.verified_by is None
    assert p.verified_at is None


def test_perspective_evaluation_lens_defaults_empty():
    p = Perspective(
        id="clinical", label="L", index=1, role="R", primary_concern="PC", failure_mode="FM"
    )
    assert p.evaluation_lens == []


def test_perspective_verified_fields_accept_values():
    p = Perspective(
        id="clinical",
        label="L",
        index=1,
        role="R",
        primary_concern="PC",
        failure_mode="FM",
        verified=True,
        verified_by="jan",
        verified_at=date(2026, 5, 19),
    )
    assert p.verified is True
    assert p.verified_by == "jan"
    assert p.verified_at == date(2026, 5, 19)


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------


def test_candidate_fields():
    c = Candidate(id="A", name="Option A")
    assert c.id == "A"
    assert c.name == "Option A"


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


def test_decision_required_fields():
    d = Decision(
        id="AD-069",
        name="Federated Learning Framework Selection",
        problem_statement="Which FL framework should we adopt?",
        planning_horizon="medium",
    )
    assert d.id == "AD-069"
    assert d.planning_horizon == "medium"


def test_decision_optional_fields_default():
    d = Decision(
        id="AD-069",
        name="N",
        problem_statement="P",
        planning_horizon="medium",
    )
    assert d.candidates == []
    assert d.perspectives == []
    assert d.requirements_filter == {}
    assert d.plateau is None


def test_decision_with_candidates_and_perspectives():
    d = Decision(
        id="AD-069",
        name="N",
        problem_statement="P",
        planning_horizon="short",
        candidates=[Candidate(id="A", name="Option A"), Candidate(id="B", name="Option B")],
        perspectives=["clinical", "security"],
        plateau=2,
    )
    assert len(d.candidates) == 2
    assert d.candidates[0].name == "Option A"
    assert "clinical" in d.perspectives
    assert d.plateau == 2
