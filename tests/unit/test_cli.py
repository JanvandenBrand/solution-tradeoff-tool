"""Unit tests for cli.py — pure helpers only (no CliRunner/API involved)."""

from pathlib import Path

import pytest

from solution_tradeoff.cli import _select_perspective_files

_FILES = [
    Path("outputs/AD-069/agents/04_data_protection.md"),
    Path("outputs/AD-069/agents/05_security.md"),
    Path("outputs/AD-069/agents/06_data_provider.md"),
]


def test_no_ids_returns_all_unchanged():
    assert _select_perspective_files(_FILES, ()) == _FILES


def test_single_matching_id_returns_just_that_file():
    result = _select_perspective_files(_FILES, ("security",))
    assert result == [Path("outputs/AD-069/agents/05_security.md")]


def test_multiple_matching_ids_preserve_file_order():
    # requested out of order — result must stay in original file order
    result = _select_perspective_files(_FILES, ("security", "data_protection"))
    assert result == [
        Path("outputs/AD-069/agents/04_data_protection.md"),
        Path("outputs/AD-069/agents/05_security.md"),
    ]


def test_unknown_id_raises_and_lists_available():
    with pytest.raises(ValueError) as exc_info:
        _select_perspective_files(_FILES, ("does_not_exist",))
    message = str(exc_info.value)
    assert "does_not_exist" in message
    assert "data_protection" in message
    assert "security" in message
    assert "data_provider" in message


def test_mix_of_known_and_unknown_only_names_unknown():
    with pytest.raises(ValueError) as exc_info:
        _select_perspective_files(_FILES, ("security", "bogus"))
    message = str(exc_info.value)
    assert "bogus" in message
    assert "security" not in message.split("Available:")[0]
