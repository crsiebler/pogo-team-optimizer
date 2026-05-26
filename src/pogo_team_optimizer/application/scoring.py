from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar, Literal

from pogo_team_optimizer.domain.models import RankingCategory, RankingProfile, RankingRow

ScoreComponentName = Literal[
    "synergy",
    "threat_coverage",
    "safety",
    "consistency",
    "bulk",
    "defensive_ratio",
    "offensive_ratio",
    "role_fit",
]
DiagnosticEntry = tuple[str, object]

MIN_PVPOKE_RANKING_SCORE = 0.0
MAX_PVPOKE_RANKING_SCORE = 100.0
NORMALIZED_PVPOKE_SCORE_MIN = 0.0
NORMALIZED_PVPOKE_SCORE_MAX = 1.0
NORMALIZED_PVPOKE_SCORE_FALLBACK = 0.5

ROSTER_COMPONENT_ORDER: tuple[ScoreComponentName, ...] = (
    "synergy",
    "threat_coverage",
    "safety",
    "consistency",
    "bulk",
    "defensive_ratio",
    "offensive_ratio",
    "role_fit",
)


@dataclass(frozen=True)
class RosterScoreWeights:
    synergy: float = 0.24
    threat_coverage: float = 0.21
    safety: float = 0.17
    consistency: float = 0.13
    bulk: float = 0.10
    defensive_ratio: float = 0.07
    offensive_ratio: float = 0.05
    role_fit: float = 0.03

    def as_mapping(self) -> dict[ScoreComponentName, float]:
        return {
            "synergy": self.synergy,
            "threat_coverage": self.threat_coverage,
            "safety": self.safety,
            "consistency": self.consistency,
            "bulk": self.bulk,
            "defensive_ratio": self.defensive_ratio,
            "offensive_ratio": self.offensive_ratio,
            "role_fit": self.role_fit,
        }


DEFAULT_ROSTER_SCORE_WEIGHTS = RosterScoreWeights()


@dataclass(frozen=True)
class PvPokeScoreNormalizationPolicy:
    """Normalize raw PvPoke category scores for weighted scoring.

    PvPoke category scores are finite values from 0 to 100. This policy keeps
    raw scores available on `RankingRow.score` and stores normalized values in
    `RankingRow.normalized_score` on a 0.0 to 1.0 scale. Invalid raw scores are
    stored with `normalized_score=None` for diagnostics, and consumer lookups use
    a neutral 0.5 fallback for missing, invalid, or degenerate category values.
    """

    fallback_score: float = NORMALIZED_PVPOKE_SCORE_FALLBACK

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.fallback_score)
            or self.fallback_score < NORMALIZED_PVPOKE_SCORE_MIN
            or self.fallback_score > NORMALIZED_PVPOKE_SCORE_MAX
        ):
            raise ValueError("fallback_score must be finite and between 0.0 and 1.0")

    def normalize_profile(self, profile: RankingProfile) -> RankingProfile:
        return RankingProfile(
            scores_by_category={
                category: self.normalize_category(rows)
                for category, rows in sorted(
                    profile.scores_by_category.items(), key=lambda item: item[0].value
                )
            }
        )

    def normalize_category(
        self,
        rows: Mapping[str, RankingRow],
    ) -> dict[str, RankingRow]:
        valid_scores = [row.score for row in rows.values() if _is_valid_pvpoke_score(row.score)]
        min_score = min(valid_scores) if valid_scores else None
        max_score = max(valid_scores) if valid_scores else None
        score_range = (
            (max_score - min_score)
            if min_score is not None and max_score is not None and max_score > min_score
            else None
        )

        normalized_rows: dict[str, RankingRow] = {}
        for species, row in sorted(rows.items(), key=lambda item: item[0]):
            normalized_score: float | None
            if not _is_valid_pvpoke_score(row.score):
                normalized_score = None
            elif score_range is None or min_score is None:
                normalized_score = self.fallback_score
            else:
                normalized_score = (row.score - min_score) / score_range
            normalized_rows[species] = RankingRow(
                species=row.species,
                score=row.score,
                normalized_score=normalized_score,
            )
        return normalized_rows

    def get_normalized_score(
        self,
        profile: RankingProfile,
        category: RankingCategory,
        species_name: str,
    ) -> float:
        rows = profile.scores_by_category.get(category)
        if rows is None:
            return self.fallback_score
        normalized_rows = self.normalize_category(rows)
        row = normalized_rows.get(species_name)
        if row is None or row.normalized_score is None:
            return self.fallback_score
        return row.normalized_score


@dataclass(frozen=True)
class ComponentScore:
    raw_value: float | None
    diagnostics: tuple[DiagnosticEntry, ...] = ()

    component_name: ClassVar[ScoreComponentName]

    def __post_init__(self) -> None:
        object.__setattr__(self, "diagnostics", _ordered_diagnostics(self.diagnostics))

    def to_weighted_component(self, weight: float) -> WeightedScoreComponent:
        diagnostics = self.diagnostics
        if self.raw_value is None and not diagnostics:
            diagnostics = (("missing", True),)
        return WeightedScoreComponent(
            name=self.component_name,
            raw_value=self.raw_value,
            weight=weight,
            diagnostics=diagnostics,
        )


@dataclass(frozen=True)
class SynergyScore(ComponentScore):
    component_name: ClassVar[ScoreComponentName] = "synergy"


@dataclass(frozen=True)
class ThreatCoverageScore(ComponentScore):
    component_name: ClassVar[ScoreComponentName] = "threat_coverage"


@dataclass(frozen=True)
class SafetyScore(ComponentScore):
    component_name: ClassVar[ScoreComponentName] = "safety"


@dataclass(frozen=True)
class ConsistencyScore(ComponentScore):
    component_name: ClassVar[ScoreComponentName] = "consistency"


@dataclass(frozen=True)
class BulkScore(ComponentScore):
    component_name: ClassVar[ScoreComponentName] = "bulk"


@dataclass(frozen=True)
class DefensiveRatioScore(ComponentScore):
    component_name: ClassVar[ScoreComponentName] = "defensive_ratio"


@dataclass(frozen=True)
class OffensiveRatioScore(ComponentScore):
    component_name: ClassVar[ScoreComponentName] = "offensive_ratio"


@dataclass(frozen=True)
class RoleFitScore(ComponentScore):
    component_name: ClassVar[ScoreComponentName] = "role_fit"


@dataclass(frozen=True)
class WeightedScoreComponent:
    name: ScoreComponentName
    raw_value: float | None
    weight: float
    diagnostics: tuple[DiagnosticEntry, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "diagnostics", _ordered_diagnostics(self.diagnostics))

    @property
    def weighted_score(self) -> float:
        if self.raw_value is None:
            return 0.0
        return self.raw_value * self.weight


@dataclass(frozen=True)
class ScoreBreakdown:
    components: tuple[WeightedScoreComponent, ...]

    @property
    def final_score(self) -> float:
        return sum(component.weighted_score for component in self.components)

    @property
    def diagnostics(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "name": component.name,
                "raw_value": component.raw_value,
                "weight": component.weight,
                "weighted_score": component.weighted_score,
                "diagnostics": component.diagnostics,
            }
            for component in self.components
        )


@dataclass(frozen=True)
class RosterScore:
    breakdown: ScoreBreakdown

    @classmethod
    def from_components(
        cls,
        *,
        synergy: SynergyScore | None = None,
        threat_coverage: ThreatCoverageScore | None = None,
        safety: SafetyScore | None = None,
        consistency: ConsistencyScore | None = None,
        bulk: BulkScore | None = None,
        defensive_ratio: DefensiveRatioScore | None = None,
        offensive_ratio: OffensiveRatioScore | None = None,
        role_fit: RoleFitScore | None = None,
        weights: RosterScoreWeights = DEFAULT_ROSTER_SCORE_WEIGHTS,
    ) -> RosterScore:
        component_scores: dict[ScoreComponentName, ComponentScore] = {
            "synergy": synergy or SynergyScore(None),
            "threat_coverage": threat_coverage or ThreatCoverageScore(None),
            "safety": safety or SafetyScore(None),
            "consistency": consistency or ConsistencyScore(None),
            "bulk": bulk or BulkScore(None),
            "defensive_ratio": defensive_ratio or DefensiveRatioScore(None),
            "offensive_ratio": offensive_ratio or OffensiveRatioScore(None),
            "role_fit": role_fit or RoleFitScore(None),
        }
        weight_by_name = weights.as_mapping()
        return cls(
            breakdown=ScoreBreakdown(
                components=tuple(
                    component_scores[name].to_weighted_component(weight_by_name[name])
                    for name in ROSTER_COMPONENT_ORDER
                )
            )
        )

    @property
    def components(self) -> tuple[WeightedScoreComponent, ...]:
        return self.breakdown.components

    @property
    def final_score(self) -> float:
        return self.breakdown.final_score

    @property
    def diagnostics(self) -> tuple[dict[str, object], ...]:
        return self.breakdown.diagnostics


def _ordered_diagnostics(
    diagnostics: tuple[DiagnosticEntry, ...],
) -> tuple[DiagnosticEntry, ...]:
    return tuple(sorted(diagnostics, key=lambda item: item[0]))


def _is_valid_pvpoke_score(score: float) -> bool:
    return (
        math.isfinite(score)
        and MIN_PVPOKE_RANKING_SCORE <= score <= MAX_PVPOKE_RANKING_SCORE
    )
