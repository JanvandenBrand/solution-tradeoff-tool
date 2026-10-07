"""AgentPromptBuilder — renders per-perspective and synthesis prompts."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


class AgentPromptBuilder:
    """Renders perspective agent prompts and the synthesis agent prompt.

    Args:
        templates_dir: Directory containing Jinja2 template files.
    """

    def __init__(self, templates_dir: Path) -> None:
        self._env = Environment(  # nosec B701 — produces Markdown, not HTML
            loader=FileSystemLoader(str(templates_dir)),
            keep_trailing_newline=True,
        )

    def build_perspective(
        self,
        context_block: str,
        perspective: dict[str, Any],
        point_budget: int,
    ) -> str:
        """Render the prompt for a single perspective agent.

        Args:
            context_block: The pre-rendered context block Markdown string.
            perspective: The perspective dict (loaded from YAML).
            point_budget: Point budget for this perspective.

        Returns:
            Rendered Markdown string.
        """
        tmpl = self._env.get_template("perspective_agent.md.j2")
        return tmpl.render(
            context_block=context_block,
            perspective=perspective,
            point_budget=point_budget,
        )

    def build_synthesis(self, perspectives: list[dict[str, Any]]) -> str:
        """Render the synthesis agent prompt.

        Args:
            perspectives: List of all perspective dicts used in the run.

        Returns:
            Rendered Markdown string.
        """
        tmpl = self._env.get_template("synthesis_agent.md.j2")
        return tmpl.render(perspectives=perspectives)

    def build_compile(
        self,
        decision: dict[str, Any],
        candidates: list[dict[str, Any]],
        perspectives: list[dict[str, Any]],
    ) -> str:
        """Render the compile prompt (used after all perspective YAMLs are collected).

        Args:
            decision: Decision dict (id, name, problem_statement, etc.).
            candidates: List of candidate dicts.
            perspectives: List of perspective dicts used in the run.

        Returns:
            Rendered Markdown string.
        """
        tmpl = self._env.get_template("compile-prompt.md.j2")
        return tmpl.render(
            decision=decision,
            candidates=candidates,
            perspectives=perspectives,
        )
