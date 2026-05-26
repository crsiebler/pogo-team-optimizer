from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

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
