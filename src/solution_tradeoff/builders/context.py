"""ContextBuilder — renders the shared context block from the Jinja2 template."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


class ContextBuilder:
    """Renders the shared 00_context.md block for all agents.

    Args:
        templates_dir: Directory containing Jinja2 template files.
    """

    def __init__(self, templates_dir: Path) -> None:
        self._env = Environment(  # nosec B701 — produces Markdown, not HTML
            loader=FileSystemLoader(str(templates_dir)),
            keep_trailing_newline=True,
        )

    def build(
        self,
        decision: dict[str, Any],
        candidates: list[dict[str, Any]],
        must_requirements: list[dict[str, Any]],
        should_requirements: list[dict[str, Any]],
        principles: list[dict[str, Any]],
        point_budget: int,
        criteria_count: int,
        architecture_decisions: list[str] | None = None,
        background_knowledge: str | None = None,
    ) -> str:
        """Render the context block.

        Args:
            decision: The 'decision' sub-dict from decision.yaml.
            candidates: List of candidate dicts.
            must_requirements: Filtered Must requirement rows.
            should_requirements: Filtered Should requirement rows.
            principles: Principle rows from xlsx.
            point_budget: Calculated point budget.
            criteria_count: Total Must + Should count.
            background_knowledge: Optional raw Markdown text of the decision's
                background knowledge briefing, appended as a trailing section.

        Returns:
            Rendered Markdown string.
        """
        all_reqs = must_requirements + should_requirements
        xlsx_ad_refs = {str(r["ad_ref"]) for r in all_reqs if r.get("ad_ref")}
        ad_refs = sorted(xlsx_ad_refs | set(architecture_decisions or []))

        tmpl = self._env.get_template("context_block.md.j2")
        return tmpl.render(
            decision=decision,
            candidates=candidates,
            must_requirements=must_requirements,
            should_requirements=should_requirements,
            principles=principles,
            point_budget=point_budget,
            criteria_count=criteria_count,
            ad_refs=ad_refs,
            background_knowledge=background_knowledge,
        )
