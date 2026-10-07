"""Unit tests for pipeline/moscow_filter.py — MoSCoWFilter."""

from solution_tradeoff.pipeline.moscow_filter import MoSCoWFilter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ROWS = [
    {
        "req_id": "R001",
        "description": "A",
        "domain": "Security",
        "moscow": "Must",
        "plateau": 1,
        "status": "Active",
    },
    {
        "req_id": "R002",
        "description": "B",
        "domain": "Security",
        "moscow": "Must",
        "plateau": 1,
        "status": "Active",
    },
    {
        "req_id": "R003",
        "description": "C",
        "domain": "Clinical",
        "moscow": "Must",
        "plateau": 2,
        "status": "Active",
    },
    {
        "req_id": "R004",
        "description": "D",
        "domain": "Clinical",
        "moscow": "Should",
        "plateau": 2,
        "status": "Active",
    },
    {
        "req_id": "R005",
        "description": "E",
        "domain": "Security",
        "moscow": "Should",
        "plateau": 1,
        "status": "Deprecated",
    },
    {
        "req_id": "R006",
        "description": "F",
        "domain": "Security",
        "moscow": "Could",
        "plateau": 1,
        "status": "Active",
    },
]

_ALL_FILTER = {"domains": [], "moscow": ["Must", "Should"]}


# ---------------------------------------------------------------------------
# Basic filtering
# ---------------------------------------------------------------------------


def test_filters_to_must_only():
    must, should = MoSCoWFilter().run(_ROWS, {"domains": [], "moscow": ["Must"]})
    assert len(should) == 0
    assert all(r["moscow"] == "Must" for r in must)


def test_filters_must_and_should():
    must, should = MoSCoWFilter().run(_ROWS, _ALL_FILTER)
    assert len(must) == 3  # R001, R002, R003 (R005 deprecated)
    assert len(should) == 1  # R004 (R005 deprecated)


def test_excludes_deprecated():
    must, should = MoSCoWFilter().run(_ROWS, _ALL_FILTER)
    ids = {r["req_id"] for r in must + should}
    assert "R005" not in ids


def test_excludes_rejected():
    rows = [{"req_id": "RX", "domain": "D", "moscow": "Must", "plateau": 1, "status": "Rejected"}]
    must, should = MoSCoWFilter().run(rows, _ALL_FILTER)
    assert len(must) == 0


def test_excludes_could():
    must, should = MoSCoWFilter().run(_ROWS, _ALL_FILTER)
    ids = {r["req_id"] for r in must + should}
    assert "R006" not in ids


# ---------------------------------------------------------------------------
# Domain filter
# ---------------------------------------------------------------------------


def test_filters_by_domain():
    must, should = MoSCoWFilter().run(
        _ROWS, {"domains": ["Security"], "moscow": ["Must", "Should"]}
    )
    ids = {r["req_id"] for r in must + should}
    assert "R003" not in ids  # Clinical domain
    assert "R004" not in ids  # Clinical domain
    assert "R001" in ids


def test_empty_domain_filter_includes_all_domains():
    must, should = MoSCoWFilter().run(_ROWS, _ALL_FILTER)
    ids = {r["req_id"] for r in must + should}
    assert "R001" in ids
    assert "R003" in ids


# ---------------------------------------------------------------------------
# Plateau filter
# ---------------------------------------------------------------------------


def test_plateau_filter_excludes_higher():
    must, should = MoSCoWFilter().run(_ROWS, _ALL_FILTER, plateau=1)
    ids = {r["req_id"] for r in must + should}
    assert "R003" not in ids  # plateau 2 > 1
    assert "R004" not in ids  # plateau 2 > 1


def test_plateau_filter_none_includes_all():
    must, _ = MoSCoWFilter().run(_ROWS, {"domains": [], "moscow": ["Must"]}, plateau=None)
    assert len(must) == 3  # R001, R002, R003


def test_plateau_none_value_not_filtered():
    rows = [{"req_id": "RX", "domain": "D", "moscow": "Must", "plateau": None, "status": "Active"}]
    must, _ = MoSCoWFilter().run(rows, {"domains": [], "moscow": ["Must"]}, plateau=1)
    assert len(must) == 1


# ---------------------------------------------------------------------------
# Sort order
# ---------------------------------------------------------------------------


def test_filter_preserves_sort_order_by_req_id():
    shuffled = [_ROWS[2], _ROWS[0], _ROWS[1]]
    must, _ = MoSCoWFilter().run(shuffled, {"domains": [], "moscow": ["Must"]})
    ids = [r["req_id"] for r in must]
    assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty():
    must, should = MoSCoWFilter().run([], _ALL_FILTER)
    assert must == []
    assert should == []


def test_case_insensitive_moscow():
    rows = [{"req_id": "R1", "domain": "D", "moscow": "MUST", "plateau": 1, "status": "Active"}]
    must, _ = MoSCoWFilter().run(rows, {"domains": [], "moscow": ["Must"]})
    assert len(must) == 1


def test_case_insensitive_status():
    rows = [{"req_id": "R1", "domain": "D", "moscow": "Must", "plateau": 1, "status": "DEPRECATED"}]
    must, _ = MoSCoWFilter().run(rows, {"domains": [], "moscow": ["Must"]})
    assert len(must) == 0
