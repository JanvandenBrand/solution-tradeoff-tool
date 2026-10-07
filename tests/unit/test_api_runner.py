"""Unit tests for runners/api_runner.py — ApiRunner and extract_yaml."""

from types import SimpleNamespace
from typing import Any

import pytest

from solution_tradeoff.runners import api_runner
from solution_tradeoff.runners.api_runner import DEFAULT_MODEL, ApiRunner, extract_yaml


class _FakeMessages:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(text="hello")])


class _FakeClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.messages = _FakeMessages()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(api_runner.anthropic, "Anthropic", _FakeClient)


def test_raises_environment_error_when_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        ApiRunner()


def test_send_returns_text_and_passes_model(client):
    runner = ApiRunner()
    assert runner.send("hi") == "hello"
    kwargs = runner._client.messages.kwargs
    assert kwargs["model"] == DEFAULT_MODEL
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]
    assert "system" not in kwargs


def test_send_includes_system_prompt_when_given(client):
    runner = ApiRunner("custom-model")
    runner.send("hi", system="context")
    kwargs = runner._client.messages.kwargs
    assert kwargs["system"] == "context"
    assert kwargs["model"] == "custom-model"


def test_extract_yaml_from_yaml_fence():
    assert extract_yaml("Intro\n```yaml\na: 1\n```\nOutro") == "a: 1"


def test_extract_yaml_from_plain_fence():
    assert extract_yaml("```\na: 1\n```") == "a: 1"


def test_extract_yaml_unfenced():
    assert extract_yaml("  a: 1\n") == "a: 1"
