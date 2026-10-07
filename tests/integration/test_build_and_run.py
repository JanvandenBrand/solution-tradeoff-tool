"""Integration tests for build-prompts, run-perspectives and run-compile.

The Claude API is never called: ApiRunner is replaced by a fake.
"""

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from solution_tradeoff import cli
from solution_tradeoff.cli import app

_XLSX = Path("examples/requirements_sample.xlsx")
_EXAMPLE_DECISION = Path("decision.yaml.example")
_VALID_FIXTURE = Path("tests/fixtures/response_valid.yaml")

_PERSPECTIVE_IDS = ["architecture", "security"]


def _write_perspective(p_dir: Path, pid: str, index: int) -> None:
    data = {
        "id": pid,
        "label": f"{pid.title()} Perspective",
        "index": index,
        "role": f"You are the {pid} lead.",
        "primary_concern": "Concern.",
        "failure_mode": "Failure.",
        "evaluation_lens": ["Question?"],
        "verified": True,
        "verified_by": "tester",
        "verified_at": None,
    }
    (p_dir / f"{pid}.yaml").write_text(yaml.dump(data))


def _make_env(tmp_path: Path, background: bool = False) -> tuple[Path, Path]:
    p_dir = tmp_path / "perspectives"
    p_dir.mkdir()
    for i, pid in enumerate(_PERSPECTIVE_IDS, start=1):
        _write_perspective(p_dir, pid, i)
    decision = yaml.safe_load(_EXAMPLE_DECISION.read_text())
    decision["perspectives"] = _PERSPECTIVE_IDS
    if background:
        (tmp_path / "background_knowledge.md").write_text("BACKGROUND-MARKER\n")
        decision["background_knowledge_path"] = "background_knowledge.md"
    dec_path = tmp_path / "decision.yaml"
    dec_path.write_text(yaml.dump(decision))
    return p_dir, dec_path


def _build(tmp_path: Path, *extra: str, background: bool = False):
    p_dir, dec_path = _make_env(tmp_path, background=background)
    return CliRunner().invoke(
        app,
        [
            "build-prompts",
            "--decision",
            str(dec_path),
            "--xlsx",
            str(_XLSX),
            "--perspectives-dir",
            str(p_dir),
            "--output",
            str(tmp_path / "outputs"),
            *extra,
        ],
    )


# ---------------------------------------------------------------------------
# build-prompts
# ---------------------------------------------------------------------------


def test_build_prompts_writes_package(tmp_path):
    result = _build(tmp_path, background=True)
    assert result.exit_code == 0, result.output
    out = tmp_path / "outputs" / "AD-001"
    agents = sorted(p.name for p in (out / "agents").iterdir())
    assert agents == ["00_context.md", "01_architecture.md", "02_security.md", "03_synthesis.md"]
    assert (out / "compile-prompt.md").exists()
    assert (out / "review.md").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["decision_id"] == "AD-001"
    context = (out / "agents" / "00_context.md").read_text()
    assert "BACKGROUND-MARKER" in context
    assert "REQ001" in context
    assert "REQ011" not in context  # deprecated
    assert "REQ010" not in context  # plateau 2


def test_build_prompts_reports_counts(tmp_path):
    result = _build(tmp_path)
    assert "8 requirements filtered (5 Must, 3 Should)" in result.output
    assert "5 principles filtered" in result.output


def test_build_prompts_dry_run_writes_nothing(tmp_path):
    result = _build(tmp_path, "--dry-run")
    assert result.exit_code == 0, result.output
    assert "[dry-run]" in result.output
    assert not (tmp_path / "outputs").exists()


def test_build_prompts_missing_config_exits_1(tmp_path):
    result = _build(tmp_path, "--config", str(tmp_path / "missing.yaml"))
    assert result.exit_code == 1
    assert "config.yaml not found" in result.output


def test_build_prompts_missing_xlsx_exits_1(tmp_path):
    p_dir, dec_path = _make_env(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "build-prompts",
            "--decision",
            str(dec_path),
            "--xlsx",
            str(tmp_path / "missing.xlsx"),
            "--perspectives-dir",
            str(p_dir),
            "--output",
            str(tmp_path / "outputs"),
        ],
    )
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# run-perspectives / run-compile with a fake ApiRunner
# ---------------------------------------------------------------------------


class _FakeRunner:
    """Stands in for ApiRunner; records calls and returns a canned response."""

    calls: list[dict[str, str | None]] = []
    response = "```yaml\n" + _VALID_FIXTURE.read_text() + "```\n"

    def __init__(self, model: str) -> None:
        self.model = model

    def send(self, user: str, system: str | None = None) -> str:
        _FakeRunner.calls.append({"user": user, "system": system})
        return _FakeRunner.response


@pytest.fixture
def fake_runner(monkeypatch):
    _FakeRunner.calls = []
    _FakeRunner.response = "```yaml\n" + _VALID_FIXTURE.read_text() + "```\n"
    monkeypatch.setattr(cli, "ApiRunner", _FakeRunner)
    return _FakeRunner


def _built(tmp_path: Path) -> Path:
    result = _build(tmp_path)
    assert result.exit_code == 0, result.output
    return tmp_path / "outputs" / "AD-001"


def _run_perspectives(out: Path, responses: Path, *extra: str):
    return CliRunner().invoke(
        app,
        [
            "run-perspectives",
            "--output-dir",
            str(out),
            "--responses-dir",
            str(responses),
            *extra,
        ],
    )


def test_run_perspectives_saves_valid_responses(tmp_path, fake_runner):
    out = _built(tmp_path)
    responses = out / "responses"
    result = _run_perspectives(out, responses)
    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in responses.iterdir()) == ["architecture.yaml", "security.yaml"]
    assert "All 2 response(s) valid" in result.output
    assert len(fake_runner.calls) == 2
    assert "Decision context" in (fake_runner.calls[0]["system"] or "")


def test_run_perspectives_filter_runs_one(tmp_path, fake_runner):
    out = _built(tmp_path)
    result = _run_perspectives(out, out / "responses", "--perspective", "security")
    assert result.exit_code == 0, result.output
    assert len(fake_runner.calls) == 1
    assert [p.name for p in (out / "responses").iterdir()] == ["security.yaml"]


def test_run_perspectives_unknown_id_exits_1(tmp_path, fake_runner):
    out = _built(tmp_path)
    result = _run_perspectives(out, out / "responses", "--perspective", "ghost")
    assert result.exit_code == 1
    assert "Unknown perspective id(s): ghost" in result.output
    assert fake_runner.calls == []


def test_run_perspectives_reports_invalid_response(tmp_path, fake_runner):
    fake_runner.response = "perspective_id: broken\n"
    out = _built(tmp_path)
    result = _run_perspectives(out, out / "responses")
    assert result.exit_code == 0
    assert "2/2 response(s) invalid" in result.output


def test_run_perspectives_missing_context_exits_1(tmp_path, fake_runner):
    result = _run_perspectives(tmp_path, tmp_path / "responses")
    assert result.exit_code == 1
    assert "Context file not found" in result.output


def test_run_perspectives_no_agent_files_warns(tmp_path, fake_runner):
    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "00_context.md").write_text("context")
    result = _run_perspectives(tmp_path, tmp_path / "responses")
    assert result.exit_code == 0
    assert "No perspective files found" in result.output


def test_run_perspectives_missing_schema_exits_1(tmp_path, fake_runner):
    out = _built(tmp_path)
    result = _run_perspectives(out, out / "responses", "--schema", str(tmp_path / "none.json"))
    assert result.exit_code == 1


def test_run_perspectives_missing_api_key_exits_1(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = _built(tmp_path)
    result = _run_perspectives(out, out / "responses")
    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY" in result.output


def _run_compile(out: Path, responses: Path, *extra: str):
    return CliRunner().invoke(
        app,
        ["run-compile", "--output-dir", str(out), "--responses-dir", str(responses), *extra],
    )


def test_run_compile_fills_placeholders_and_writes_analysis(tmp_path, fake_runner):
    out = _built(tmp_path)
    _run_perspectives(out, out / "responses")
    fake_runner.calls = []
    fake_runner.response = "# Analysis\n"
    result = _run_compile(out, out / "responses")
    assert result.exit_code == 0, result.output
    assert (out / "analysis.md").read_text() == "# Analysis\n"
    prompt = fake_runner.calls[0]["user"] or ""
    assert "YAML HERE]" not in prompt
    assert "preferred_option" in prompt


def test_run_compile_warns_on_missing_responses_and_custom_output(tmp_path, fake_runner):
    out = _built(tmp_path)
    responses = out / "responses"
    responses.mkdir()
    target = tmp_path / "report.md"
    result = _run_compile(out, responses, "--output", str(target))
    assert result.exit_code == 0, result.output
    assert "No YAML found for: architecture, security" in result.output
    assert target.exists()


def test_run_compile_missing_prompt_exits_1(tmp_path, fake_runner):
    result = _run_compile(tmp_path, tmp_path)
    assert result.exit_code == 1
    assert "Compile prompt not found" in result.output


def test_run_compile_missing_responses_dir_exits_1(tmp_path, fake_runner):
    out = _built(tmp_path)
    result = _run_compile(out, tmp_path / "nope")
    assert result.exit_code == 1
    assert "Responses directory not found" in result.output


def test_run_compile_missing_api_key_exits_1(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = _built(tmp_path)
    (out / "responses").mkdir()
    result = _run_compile(out, out / "responses")
    assert result.exit_code == 1
