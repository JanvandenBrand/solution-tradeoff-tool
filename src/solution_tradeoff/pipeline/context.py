"""PipelineContext — snapshot of all data assembled during a build-prompts run."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineContext:
    """Holds all data assembled during a build-prompts run.

    Attributes:
        decision: The decision sub-dict (id, name, problem_statement, planning_horizon, plateau).
        candidates: List of candidate dicts (id, name).
        must_reqs: Filtered Must requirement rows.
        should_reqs: Filtered Should requirement rows.
        principles: Principle rows from the Principles xlsx sheet.
        ad_refs: Unique AD references derived from requirements (may be empty).
        perspective_objects: Perspective dicts for all selected perspectives.
        point_budget: Calculated point budget per perspective agent.
        criteria_count: Total Must + Should count.
    """

    decision: dict[str, Any]
    candidates: list[dict[str, Any]]
    must_reqs: list[dict[str, Any]] = field(default_factory=list)
    should_reqs: list[dict[str, Any]] = field(default_factory=list)
    principles: list[dict[str, Any]] = field(default_factory=list)
    ad_refs: list[str] = field(default_factory=list)
    perspective_objects: list[dict[str, Any]] = field(default_factory=list)
    point_budget: int = 0
    criteria_count: int = 0
