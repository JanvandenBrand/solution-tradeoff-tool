"""Requirement dataclass."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Requirement:
    """A single requirement row loaded from the xlsx requirements sheet."""

    req_id: str
    description: str
    domain: str
    moscow: str
    status: str
    plateau: Optional[int] = None
    apr_ref: Optional[str] = None
    ad_ref: Optional[str] = None
