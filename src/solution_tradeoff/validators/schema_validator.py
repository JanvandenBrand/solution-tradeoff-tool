"""SchemaValidator — validates agent YAML response files against the tradeoff schema."""

import json
from pathlib import Path

import jsonschema
import yaml


class ValidationError:
    """Single schema validation error for one response file."""

    def __init__(self, file: Path, message: str) -> None:
        self.file = file
        self.message = message

    def __str__(self) -> str:
        return f"{self.file.name}: {self.message}"


class SchemaValidator:
    """Validates perspective agent YAML response files against the JSON schema.

    Args:
        schema_path: Path to the JSON Schema file.
    """

    def __init__(self, schema_path: Path) -> None:
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        with open(schema_path) as fh:
            self._schema = json.load(fh)

    def validate_file(self, path: Path) -> list[ValidationError]:
        """Validate a single YAML response file.

        Returns:
            List of ValidationError instances (empty if valid).

        Raises:
            ValueError: If the file is not valid YAML.
        """
        with open(path) as fh:
            try:
                data = yaml.safe_load(fh)
            except yaml.YAMLError as exc:
                return [ValidationError(path, f"Invalid YAML: {exc}")]

        if not isinstance(data, dict):
            return [ValidationError(path, f"Expected a YAML mapping, got {type(data).__name__}")]

        validator = jsonschema.Draft202012Validator(self._schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: str(e.path))
        return [
            ValidationError(
                path, f"{'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            )
            for e in errors
        ]

    def validate_directory(self, responses_dir: Path) -> dict[Path, list[ValidationError]]:
        """Validate all *.yaml files in responses_dir.

        Returns:
            Dict mapping each file path to its list of errors (empty list = valid).

        Raises:
            FileNotFoundError: If responses_dir does not exist.
        """
        if not responses_dir.exists():
            raise FileNotFoundError(f"Responses directory not found: {responses_dir}")

        results: dict[Path, list[ValidationError]] = {}
        for path in sorted(responses_dir.glob("*.yaml")):
            results[path] = self.validate_file(path)
        return results
