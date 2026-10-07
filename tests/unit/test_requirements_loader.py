"""Unit tests for loaders/requirements.py — RequirementsLoader."""

import warnings
from pathlib import Path

import openpyxl
import pytest

from solution_tradeoff.loaders.requirements import RequirementsLoader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CFG = {
    "xlsx": {
        "requirements_sheet": "Requirements",
        "principles_sheet": "Principles",
        "columns": {
            "req_id": "Ref",
            "description": "Requirement",
            "domain": "Category",
            "moscow": "MoSCoW",
            "plateau": "Plateau",
            "status": "Status",
            "apr_ref": "APR Link",
            "ad_ref": "AD Ref",
        },
        "principles_columns": {
            "principle_id": "Ref",
            "description": "Architecture Principle",
            "domain": "Category",
        },
    }
}


def _make_xlsx(tmp_path: Path, req_rows: list[tuple], pri_rows: list[tuple] | None = None) -> Path:
    wb = openpyxl.Workbook()
    req = wb.active
    req.title = "Requirements"
    req.append(
        ["Ref", "Requirement", "Category", "MoSCoW", "Plateau", "Status", "APR Link", "AD Ref"]
    )
    for row in req_rows:
        req.append(row)

    pri = wb.create_sheet("Principles")
    pri.append(["Ref", "Architecture Principle", "Category"])
    for row in pri_rows or [("APR-01", "Be cloud-agnostic", "Architecture")]:
        pri.append(row)

    path = tmp_path / "reqs.xlsx"
    wb.save(path)
    return path


_REQ_ROWS: list[tuple] = [
    ("REQ-001", "Encrypt at rest", "Security", "Must", 1, "Active", "APR-01", None),
    ("REQ-002", "Enforce MFA", "Security", "Must", 1, "Active", "APR-01", "AD-001"),
    ("REQ-003", "FL without raw data leaving", "Technology", "Must", 1, "Active", None, None),
    ("REQ-004", "Audit trail", "Security", "Must", 1, "Active", "APR-02", None),
    ("REQ-005", "Support EHDS", "Technology", "Must", 2, "Active", None, None),
    ("REQ-006", "Deploy in Azure", "Technology", "Must", 1, "Active", None, "AD-001"),
    ("REQ-007", "10 concurrent jobs", "Technology", "Should", 2, "Active", None, None),
    ("REQ-008", "API for submission", "Technology", "Should", 2, "Active", None, None),
    ("REQ-009", "Differential privacy", "Security", "Should", 2, "Active", "APR-01", None),
    ("REQ-010", "PDF reports", "Technology", "Could", 3, "Active", None, None),
    ("REQ-011", "Old approach", "Technology", "Must", 1, "Deprecated", None, None),
]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_loads_all_required_columns(tmp_path):
    path = _make_xlsx(tmp_path, _REQ_ROWS)
    loader = RequirementsLoader(_CFG)
    rows, _ = loader.load(path)
    # 11 data rows minus 1 empty check — all present (deprecated row still loaded here)
    assert len(rows) == 11
    assert rows[0]["req_id"] == "REQ-001"
    assert rows[0]["moscow"] == "Must"
    assert rows[0]["status"] == "Active"


def test_loads_principles(tmp_path):
    path = _make_xlsx(tmp_path, _REQ_ROWS)
    loader = RequirementsLoader(_CFG)
    _, principles = loader.load(path)
    assert len(principles) == 1
    assert principles[0]["principle_id"] == "APR-01"


def test_example_file_loads():
    """The shipped example spreadsheet must load without error."""
    example = Path("examples/requirements_sample.xlsx")
    loader = RequirementsLoader(_CFG)
    rows, principles = loader.load(example)
    assert len(rows) == 12  # 11 active + 1 deprecated
    assert len(principles) == 5


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_raises_on_missing_file(tmp_path):
    loader = RequirementsLoader(_CFG)
    with pytest.raises(FileNotFoundError):
        loader.load(tmp_path / "missing.xlsx")


def test_raises_on_missing_required_column(tmp_path):
    wb = openpyxl.Workbook()
    req = wb.active
    req.title = "Requirements"
    req.append(["Ref", "Requirement", "Category", "MoSCoW", "Plateau"])  # no Status column
    pri = wb.create_sheet("Principles")
    pri.append(["Ref", "Architecture Principle", "Category"])
    path = tmp_path / "bad.xlsx"
    wb.save(path)
    loader = RequirementsLoader(_CFG)
    with pytest.raises(ValueError, match="Status"):
        loader.load(path)


def test_raises_on_missing_sheet(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.title = "Requirements"
    wb.active.append(["Ref", "Requirement", "Category", "MoSCoW", "Plateau", "Status"])
    path = tmp_path / "nopri.xlsx"
    wb.save(path)
    loader = RequirementsLoader(_CFG)
    with pytest.raises(ValueError, match="Principles"):
        loader.load(path)


def test_warns_when_plateau_column_absent(tmp_path):
    wb = openpyxl.Workbook()
    req = wb.active
    req.title = "Requirements"
    req.append(["Ref", "Requirement", "Category", "MoSCoW", "Status"])
    req.append(["REQ-001", "X", "Y", "Must", "Active"])
    pri = wb.create_sheet("Principles")
    pri.append(["Ref", "Architecture Principle", "Category"])
    path = tmp_path / "noplateau.xlsx"
    wb.save(path)

    # Config still asks for plateau column with wrong name
    cfg_wrong = {
        "xlsx": {
            **_CFG["xlsx"],
            "columns": {**_CFG["xlsx"]["columns"], "plateau": "WrongPlateauHeader"},
        }
    }
    loader = RequirementsLoader(cfg_wrong)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        rows, _ = loader.load(path)
        assert any("plateau" in str(warning.message).lower() for warning in w)
    assert rows[0]["plateau"] is None


# ---------------------------------------------------------------------------
# MoSCoW parsing
# ---------------------------------------------------------------------------


def test_moscow_values_preserved_as_loaded(tmp_path):
    """Loader preserves raw MoSCoW values — filtering is MoSCoWFilter's job."""
    path = _make_xlsx(tmp_path, _REQ_ROWS)
    loader = RequirementsLoader(_CFG)
    rows, _ = loader.load(path)
    moscow_values = {r["moscow"] for r in rows}
    assert "Must" in moscow_values
    assert "Should" in moscow_values
    assert "Could" in moscow_values


# ---------------------------------------------------------------------------
# Empty rows
# ---------------------------------------------------------------------------


def test_skips_empty_rows(tmp_path):
    wb = openpyxl.Workbook()
    req = wb.active
    req.title = "Requirements"
    req.append(
        ["Ref", "Requirement", "Category", "MoSCoW", "Plateau", "Status", "APR Link", "AD Ref"]
    )
    req.append(["REQ-001", "X", "Y", "Must", 1, "Active", None, None])
    req.append([None, None, None, None, None, None, None, None])  # empty row
    req.append(["REQ-002", "Z", "W", "Should", 1, "Active", None, None])
    pri = wb.create_sheet("Principles")
    pri.append(["Ref", "Architecture Principle", "Category"])
    path = tmp_path / "gaps.xlsx"
    wb.save(path)
    loader = RequirementsLoader(_CFG)
    rows, _ = loader.load(path)
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# APR Ref / AD Ref columns
# ---------------------------------------------------------------------------


def test_loads_apr_ref_values(tmp_path):
    path = _make_xlsx(tmp_path, _REQ_ROWS)
    loader = RequirementsLoader(_CFG)
    rows, _ = loader.load(path)
    assert rows[0]["apr_ref"] == "APR-01"
    assert rows[2]["apr_ref"] is None


def test_loads_ad_ref_values(tmp_path):
    path = _make_xlsx(tmp_path, _REQ_ROWS)
    loader = RequirementsLoader(_CFG)
    rows, _ = loader.load(path)
    assert rows[1]["ad_ref"] == "AD-001"
    assert rows[0]["ad_ref"] is None


def test_warns_when_apr_ref_column_absent(tmp_path):
    wb = openpyxl.Workbook()
    req = wb.active
    req.title = "Requirements"
    req.append(["Ref", "Requirement", "Category", "MoSCoW", "Plateau", "Status"])
    req.append(["REQ-001", "X", "Y", "Must", 1, "Active"])
    pri = wb.create_sheet("Principles")
    pri.append(["Ref", "Architecture Principle", "Category"])
    path = tmp_path / "noapr.xlsx"
    wb.save(path)
    loader = RequirementsLoader(_CFG)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        rows, _ = loader.load(path)
        messages = [str(warning.message) for warning in w]
        assert any("apr_ref" in m for m in messages)
        assert any("ad_ref" in m for m in messages)
    assert rows[0]["apr_ref"] is None
    assert rows[0]["ad_ref"] is None
