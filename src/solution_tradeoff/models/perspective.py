"""Perspective dataclass."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Perspective:
    """A stakeholder perspective loaded from perspectives/<id>.yaml."""

    id: str
    label: str
    index: int
    role: str
    primary_concern: str
    failure_mode: str
    evaluation_lens: list[str] = field(default_factory=list)
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[date] = None
