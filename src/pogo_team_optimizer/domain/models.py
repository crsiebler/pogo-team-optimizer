from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ShieldScenario(int, Enum):
    ZERO = 0
    ONE = 1
    TWO = 2


@dataclass(frozen=True)
class TeamMember:
    index: int
    label: str
    species: str
    base_species: str
    types: tuple[str, ...]


@dataclass(frozen=True)
class TeamRecommendation:
    members: tuple[TeamMember, ...]
    score: tuple[float, ...]
    shadow_count: int


@dataclass(frozen=True)
class CoverageSummary:
    shield: ShieldScenario
    wins: int
    draws: int
    losses: int
    weighted_wins: float


@dataclass(frozen=True)
class Threat:
    opponent_label: str
    min_best_score: int
    avg_best_score: float
    shield_best_scores: tuple[int, int, int]
    shield_best_members: tuple[str, str, str]


@dataclass(frozen=True)
class CorePlan:
    members: tuple[TeamMember, ...]
    score: tuple[float, ...]


@dataclass(frozen=True)
class TargetMapEntry:
    opponent_label: str
    shield_best_scores: tuple[int, int, int]
    shield_best_members: tuple[str, str, str]
    confidence: str


@dataclass(frozen=True)
class AnalysisResult:
    recommended_team: TeamRecommendation
    coverage: tuple[CoverageSummary, ...]
    threats: tuple[Threat, ...]
    safe_cores: tuple[CorePlan, ...]
    target_map: tuple[TargetMapEntry, ...]
