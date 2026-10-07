"""Decision and Candidate dataclasses."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Candidate:
    """A solution candidate being evaluated."""

    id: str
    name: str


@dataclass
class Decision:
    """A loaded decision.yaml, representing one trade-off analysis."""

    id: str
    name: str
    problem_statement: str
    planning_horizon: str
    candidates: list[Candidate] = field(default_factory=list)
    perspectives: list[str] = field(default_factory=list)
    requirements_filter: dict[str, Any] = field(default_factory=dict[str, Any])
    plateau: Optional[int] = None
    architecture_decisions: list[str] = field(default_factory=list)
    background_knowledge_path: Optional[str] = None
