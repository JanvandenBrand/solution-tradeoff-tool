"""Unit tests for validators/schema_validator.py — SchemaValidator."""

from pathlib import Path

import pytest
import yaml

from solution_tradeoff.validators.schema_validator import SchemaValidator, ValidationError

_SCHEMA = Path("schemas/tradeoff-output.schema.json")
_VALID_FIXTURE = Path("tests/fixtures/response_valid.yaml")
_INVALID_FIXTURE = Path("tests/fixtures/response_invalid.yaml")


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_raises_on_missing_schema(tmp_path):
    with pytest.raises(FileNotFoundError, match="Schema file not found"):
        SchemaValidator(tmp_path / "missing.json")


# ---------------------------------------------------------------------------
# validate_file — valid input
# ---------------------------------------------------------------------------


def test_valid_fixture_passes():
    validator = SchemaValidator(_SCHEMA)
    errors = validator.validate_file(_VALID_FIXTURE)
    assert errors == []


def test_valid_minimal_passes(tmp_path):
    data = {
        "perspective_id": "clinical",
        "concerns": [{"concern": "X", "risk": "Y"}],
        "point_allocations": [{"criterion_id": "REQ001", "points": 10, "rationale": "Z"}],
        "preferred_option": "A",
    }
    path = tmp_path / "minimal.yaml"
    path.write_text(yaml.dump(data))
    validator = SchemaValidator(_SCHEMA)
    assert validator.validate_file(path) == []


# ---------------------------------------------------------------------------
# validate_file — invalid inputs
# ---------------------------------------------------------------------------


def test_invalid_fixture_fails():
    validator = SchemaValidator(_SCHEMA)
    errors = validator.validate_file(_INVALID_FIXTURE)
    assert len(errors) > 0


def test_missing_required_field_reported(tmp_path):
    data = {"perspective_id": "clinical", "preferred_option": "A"}  # missing concerns + allocs
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.dump(data))
    validator = SchemaValidator(_SCHEMA)
    errors = validator.validate_file(path)
    messages = [e.message for e in errors]
    assert any("concerns" in m for m in messages)
    assert any("point_allocations" in m for m in messages)


def test_negative_points_rejected(tmp_path):
    data = {
        "perspective_id": "clinical",
        "concerns": [{"concern": "X", "risk": "Y"}],
        "point_allocations": [{"criterion_id": "REQ001", "points": -5, "rationale": "Z"}],
        "preferred_option": "A",
    }
    path = tmp_path / "neg.yaml"
    path.write_text(yaml.dump(data))
    validator = SchemaValidator(_SCHEMA)
    errors = validator.validate_file(path)
    assert any("points" in e.message for e in errors)


def test_extra_field_rejected(tmp_path):
    data = {
        "perspective_id": "clinical",
        "concerns": [{"concern": "X", "risk": "Y"}],
        "point_allocations": [{"criterion_id": "REQ001", "points": 10, "rationale": "Z"}],
        "preferred_option": "A",
        "unknown_field": "bad",
    }
    path = tmp_path / "extra.yaml"
    path.write_text(yaml.dump(data))
    validator = SchemaValidator(_SCHEMA)
    errors = validator.validate_file(path)
    assert len(errors) > 0


def test_invalid_yaml_returns_error(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("key: [\nunclosed bracket")
    validator = SchemaValidator(_SCHEMA)
    errors = validator.validate_file(path)
    assert len(errors) == 1
    assert "Invalid YAML" in errors[0].message


def test_non_mapping_yaml_returns_error(tmp_path):
    path = tmp_path / "list.yaml"
    path.write_text("- a\n- b\n")
    validator = SchemaValidator(_SCHEMA)
    errors = validator.validate_file(path)
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# validate_directory
# ---------------------------------------------------------------------------


def test_validate_directory_valid(tmp_path):
    import shutil

    shutil.copy(_VALID_FIXTURE, tmp_path / "clinical.yaml")
    validator = SchemaValidator(_SCHEMA)
    results = validator.validate_directory(tmp_path)
    assert len(results) == 1
    assert list(results.values())[0] == []


def test_validate_directory_mixed(tmp_path):
    import shutil

    shutil.copy(_VALID_FIXTURE, tmp_path / "clinical.yaml")
    shutil.copy(_INVALID_FIXTURE, tmp_path / "security.yaml")
    validator = SchemaValidator(_SCHEMA)
    results = validator.validate_directory(tmp_path)
    assert len(results) == 2
    errors_by_name = {p.name: errs for p, errs in results.items()}
    assert errors_by_name["clinical.yaml"] == []
    assert len(errors_by_name["security.yaml"]) > 0


def test_validate_directory_missing_dir(tmp_path):
    validator = SchemaValidator(_SCHEMA)
    with pytest.raises(FileNotFoundError, match="Responses directory not found"):
        validator.validate_directory(tmp_path / "nonexistent")


def test_validate_directory_empty_returns_empty_dict(tmp_path):
    validator = SchemaValidator(_SCHEMA)
    results = validator.validate_directory(tmp_path)
    assert results == {}


# ---------------------------------------------------------------------------
# ValidationError str representation
# ---------------------------------------------------------------------------


def test_validation_error_str():
    err = ValidationError(Path("clinical.yaml"), "concerns: required")
    assert "clinical.yaml" in str(err)
    assert "concerns" in str(err)
