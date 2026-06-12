from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal

from pogo_team_optimizer.domain.models import RankingCategory, RankingProfile, RankingRow

SoftMatchupBand = Literal[
    "strong_answer",
    "playable_answer",
    "neutral_matchup",
    "soft_loss",
    "hard_loss",
]
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
WIN_SCORE_THRESHOLD = 500
OVERWHELMING_LOSS_SCORE_THRESHOLD = 400
TOP_THREAT_COVERAGE_WEIGHT = 0.75
FULL_META_COVERAGE_WEIGHT = 0.25
SHIELD_SCENARIO_WEIGHTS: tuple[float, float, float] = (0.30, 0.50, 0.20)
STRONG_ANSWER_SCORE_THRESHOLD = 600
PLAYABLE_ANSWER_SCORE_THRESHOLD = 525
NEUTRAL_MATCHUP_SCORE_THRESHOLD = 475

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


def calculate_ranking_aware_roster_score(
    *,
    team_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    bulk_by_row: Sequence[float],
    safety_by_row: Sequence[float] | None = None,
    consistency_by_row: Sequence[float] | None = None,
    pokemon_types_by_row: Sequence[tuple[str, ...]] | None = None,
    move_types_by_row: Sequence[tuple[str, ...]] | None = None,
    opponent_types_by_col: Sequence[tuple[str, ...]] | None = None,
    type_effectiveness: Mapping[str, Mapping[str, float]] | None = None,
    top_threat_indices: Sequence[int] | None = None,
    full_meta_indices: Sequence[int] | None = None,
) -> RosterScore:
    col_count = len(matrices[0][0]) if matrices and matrices[0] else 0
    full_meta = tuple(range(col_count)) if full_meta_indices is None else tuple(full_meta_indices)
    top_threats = (
        full_meta[: min(10, len(full_meta))]
        if top_threat_indices is None
        else tuple(top_threat_indices)
    )
    _validate_threat_indices(top_threats, col_count)
    _validate_threat_indices(full_meta, col_count)
    coverage_score, no_answer_top, no_answer_full, single_top, single_full = _coverage_component(
        team_indices,
        matrices,
        top_threats,
        full_meta,
    )
    safety_score, overwhelming_losses, shield_fragility = _safety_component(
        team_indices,
        matrices,
        top_threats,
        full_meta,
        safety_by_row,
    )
    consistency_score, shield_stability = _consistency_component(
        team_indices,
        matrices,
        full_meta,
        consistency_by_row,
    )
    bulk_score = _bulk_component(team_indices, bulk_by_row)
    defensive_ratio = _defensive_ratio_component(
        team_indices,
        pokemon_types_by_row,
        opponent_types_by_col,
        type_effectiveness,
        top_threats,
        full_meta,
    )
    offensive_ratio = _offensive_ratio_component(
        team_indices,
        move_types_by_row,
        opponent_types_by_col,
        type_effectiveness,
        top_threats,
        full_meta,
    )

    return RosterScore.from_components(
        synergy=SynergyScore(
            NORMALIZED_PVPOKE_SCORE_FALLBACK,
            diagnostics=(("neutral_fallback", True),),
        ),
        threat_coverage=ThreatCoverageScore(
            coverage_score,
            diagnostics=(
                ("full_meta_no_answer", no_answer_full),
                ("full_meta_single_answer", single_full),
                ("top_threat_no_answer", no_answer_top),
                ("top_threat_single_answer", single_top),
            ),
        ),
        safety=SafetyScore(
            safety_score,
            diagnostics=(
                ("overwhelming_losses", overwhelming_losses),
                ("shield_fragility", shield_fragility),
            ),
        ),
        consistency=ConsistencyScore(
            consistency_score,
            diagnostics=(
                ("bait_dependence_proxy", round(1.0 - shield_stability, 6)),
                ("move_dpe_proxy", NORMALIZED_PVPOKE_SCORE_FALLBACK),
                ("shield_stability", shield_stability),
            ),
        ),
        bulk=BulkScore(
            bulk_score,
            diagnostics=(
                ("pool_max", max(bulk_by_row) if bulk_by_row else 0.0),
                ("pool_min", min(bulk_by_row) if bulk_by_row else 0.0),
            ),
        ),
        defensive_ratio=DefensiveRatioScore(
            defensive_ratio if defensive_ratio is not None else NORMALIZED_PVPOKE_SCORE_FALLBACK,
            diagnostics=(("missing_type_data", True),) if defensive_ratio is None else (),
        ),
        offensive_ratio=OffensiveRatioScore(
            offensive_ratio if offensive_ratio is not None else NORMALIZED_PVPOKE_SCORE_FALLBACK,
            diagnostics=(("missing_move_or_type_data", True),) if offensive_ratio is None else (),
        ),
        role_fit=RoleFitScore(
            NORMALIZED_PVPOKE_SCORE_FALLBACK,
            diagnostics=(("neutral_fallback", True),),
        ),
    )


def aggregate_shield_matchup_score(scores_by_shield: Sequence[float]) -> float:
    """Return weighted matchup strength across available 0-, 1-, and 2-shield scores."""
    if not scores_by_shield or len(scores_by_shield) > len(SHIELD_SCENARIO_WEIGHTS):
        raise ValueError("shield matchup scores must contain one to three values")
    if any(not math.isfinite(score) for score in scores_by_shield):
        raise ValueError("shield matchup scores must be finite")

    available_weights = SHIELD_SCENARIO_WEIGHTS[: len(scores_by_shield)]
    weight_total = sum(available_weights)
    return sum(
        score * weight for score, weight in zip(scores_by_shield, available_weights, strict=True)
    ) / weight_total


def classify_soft_matchup_score(score: float) -> SoftMatchupBand:
    if not math.isfinite(score):
        raise ValueError("matchup score must be finite")
    if score >= STRONG_ANSWER_SCORE_THRESHOLD:
        return "strong_answer"
    if score >= PLAYABLE_ANSWER_SCORE_THRESHOLD:
        return "playable_answer"
    if score >= NEUTRAL_MATCHUP_SCORE_THRESHOLD:
        return "neutral_matchup"
    if score >= OVERWHELMING_LOSS_SCORE_THRESHOLD:
        return "soft_loss"
    return "hard_loss"


def soft_matchup_quality(score: float) -> float:
    """Map a PvPoke-style battle rating to bounded higher-is-better quality."""
    if not math.isfinite(score):
        raise ValueError("matchup score must be finite")
    return _clamp(score / 1000.0)


def soft_matchup_risk(score: float) -> float:
    """Return lower-is-better risk, with hard losses worse than marginal losses."""
    if not math.isfinite(score):
        raise ValueError("matchup score must be finite")
    if score >= WIN_SCORE_THRESHOLD:
        return 0.0
    loss_severity = (WIN_SCORE_THRESHOLD - max(0.0, score)) / WIN_SCORE_THRESHOLD
    return _clamp(loss_severity * loss_severity)


def shield_stability_score(scores_by_shield: Sequence[float]) -> float:
    """Score matchup quality after penalizing shield-path volatility."""
    aggregate_score = aggregate_shield_matchup_score(scores_by_shield)
    spread = max(scores_by_shield) - min(scores_by_shield)
    volatility_penalty = _clamp(spread / 1000.0)
    return _clamp(soft_matchup_quality(aggregate_score) * (1.0 - volatility_penalty))


def count_playable_soft_answers(scores_by_member: Sequence[Sequence[float]]) -> int:
    return sum(
        1
        for scores_by_shield in scores_by_member
        if aggregate_shield_matchup_score(scores_by_shield) >= PLAYABLE_ANSWER_SCORE_THRESHOLD
    )


def _ordered_diagnostics(
    diagnostics: tuple[DiagnosticEntry, ...],
) -> tuple[DiagnosticEntry, ...]:
    return tuple(sorted(diagnostics, key=lambda item: item[0]))


def _is_valid_pvpoke_score(score: float) -> bool:
    return (
        math.isfinite(score)
        and MIN_PVPOKE_RANKING_SCORE <= score <= MAX_PVPOKE_RANKING_SCORE
    )


def _validate_threat_indices(indices: Sequence[int], col_count: int) -> None:
    invalid_indices = [index for index in indices if index < 0 or index >= col_count]
    if invalid_indices:
        raise ValueError(
            "threat indices must be between 0 and "
            f"{max(0, col_count - 1)}; got {invalid_indices}"
        )


def _coverage_component(
    team_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    top_threat_indices: Sequence[int],
    full_meta_indices: Sequence[int],
) -> tuple[float, int, int, int, int]:
    top_no_answer, top_single_answer = _answer_counts(team_indices, matrices, top_threat_indices)
    full_no_answer, full_single_answer = _answer_counts(team_indices, matrices, full_meta_indices)
    top_miss_rate = top_no_answer / len(top_threat_indices) if top_threat_indices else 0.0
    full_miss_rate = full_no_answer / len(full_meta_indices) if full_meta_indices else 0.0
    top_single_rate = top_single_answer / len(top_threat_indices) if top_threat_indices else 0.0
    full_single_rate = full_single_answer / len(full_meta_indices) if full_meta_indices else 0.0
    penalty = (
        TOP_THREAT_COVERAGE_WEIGHT * (top_miss_rate + (0.35 * top_single_rate))
        + FULL_META_COVERAGE_WEIGHT * (full_miss_rate + (0.20 * full_single_rate))
    )
    return _clamp(1.0 - penalty), top_no_answer, full_no_answer, top_single_answer, full_single_answer


def _answer_counts(
    team_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    threat_indices: Sequence[int],
) -> tuple[int, int]:
    no_answer = 0
    single_answer = 0
    for col_idx in threat_indices:
        winners = sum(
            1
            for row_idx in team_indices
            if max(matrix[row_idx][col_idx] for matrix in matrices) > WIN_SCORE_THRESHOLD
        )
        if winners == 0:
            no_answer += 1
        elif winners == 1:
            single_answer += 1
    return no_answer, single_answer


def _safety_component(
    team_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    top_threat_indices: Sequence[int],
    full_meta_indices: Sequence[int],
    safety_by_row: Sequence[float] | None,
) -> tuple[float, int, float]:
    top_no_answer, top_single_answer = _answer_counts(team_indices, matrices, top_threat_indices)
    full_no_answer, full_single_answer = _answer_counts(team_indices, matrices, full_meta_indices)
    overwhelming_losses = _overwhelming_loss_count(team_indices, matrices, full_meta_indices)
    shield_fragility = _shield_fragility(team_indices, matrices, full_meta_indices)
    top_count = len(top_threat_indices) or 1
    full_count = len(full_meta_indices) or 1
    safe_swap_quality = _average_indexed_values(team_indices, safety_by_row, NORMALIZED_PVPOKE_SCORE_FALLBACK)
    if safe_swap_quality > 1.0:
        safe_swap_quality /= 100.0
    penalty = (
        0.30 * (top_no_answer / top_count)
        + 0.18 * (top_single_answer / top_count)
        + 0.15 * (full_no_answer / full_count)
        + 0.10 * (full_single_answer / full_count)
        + 0.17 * (overwhelming_losses / full_count)
        + 0.10 * shield_fragility
    )
    score = (0.85 * (1.0 - penalty)) + (0.15 * safe_swap_quality)
    return _clamp(score), overwhelming_losses, round(shield_fragility, 6)


def _consistency_component(
    team_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    full_meta_indices: Sequence[int],
    consistency_by_row: Sequence[float] | None,
) -> tuple[float, float]:
    ranking_consistency = _average_indexed_values(
        team_indices,
        consistency_by_row,
        NORMALIZED_PVPOKE_SCORE_FALLBACK,
    )
    shield_stability = 1.0 - _shield_fragility(team_indices, matrices, full_meta_indices)
    score = (0.60 * ranking_consistency) + (0.30 * shield_stability) + (
        0.10 * NORMALIZED_PVPOKE_SCORE_FALLBACK
    )
    return _clamp(score), round(shield_stability, 6)


def _bulk_component(team_indices: Sequence[int], bulk_by_row: Sequence[float]) -> float:
    if not team_indices or not bulk_by_row:
        return NORMALIZED_PVPOKE_SCORE_FALLBACK
    pool_min = min(bulk_by_row)
    pool_max = max(bulk_by_row)
    if pool_max <= pool_min:
        return NORMALIZED_PVPOKE_SCORE_FALLBACK
    team_average = sum(bulk_by_row[index] for index in team_indices) / len(team_indices)
    return _clamp((team_average - pool_min) / (pool_max - pool_min))


def _defensive_ratio_component(
    team_indices: Sequence[int],
    pokemon_types_by_row: Sequence[tuple[str, ...]] | None,
    opponent_types_by_col: Sequence[tuple[str, ...]] | None,
    type_effectiveness: Mapping[str, Mapping[str, float]] | None,
    top_threat_indices: Sequence[int],
    full_meta_indices: Sequence[int],
) -> float | None:
    if not pokemon_types_by_row or not opponent_types_by_col or not type_effectiveness:
        return None
    return _weighted_pool_type_score(
        top_threat_indices,
        full_meta_indices,
        lambda col_idx: _defensive_threat_score(
            team_indices,
            pokemon_types_by_row,
            opponent_types_by_col[col_idx],
            type_effectiveness,
        ),
    )


def _offensive_ratio_component(
    team_indices: Sequence[int],
    move_types_by_row: Sequence[tuple[str, ...]] | None,
    opponent_types_by_col: Sequence[tuple[str, ...]] | None,
    type_effectiveness: Mapping[str, Mapping[str, float]] | None,
    top_threat_indices: Sequence[int],
    full_meta_indices: Sequence[int],
) -> float | None:
    if not move_types_by_row or not opponent_types_by_col or not type_effectiveness:
        return None
    move_types = tuple(
        move_type
        for row_idx in team_indices
        for move_type in move_types_by_row[row_idx]
        if move_type in type_effectiveness
    )
    if not move_types:
        return None
    return _weighted_pool_type_score(
        top_threat_indices,
        full_meta_indices,
        lambda col_idx: _offensive_threat_score(
            move_types,
            opponent_types_by_col[col_idx],
            type_effectiveness,
        ),
    )


def _weighted_pool_type_score(
    top_threat_indices: Sequence[int],
    full_meta_indices: Sequence[int],
    scorer: Callable[[int], float],
) -> float:
    top_score = _average_threat_type_score(top_threat_indices, scorer)
    full_score = _average_threat_type_score(full_meta_indices, scorer)
    return _clamp((TOP_THREAT_COVERAGE_WEIGHT * top_score) + (FULL_META_COVERAGE_WEIGHT * full_score))


def _average_threat_type_score(
    threat_indices: Sequence[int],
    scorer: Callable[[int], float],
) -> float:
    if not threat_indices:
        return NORMALIZED_PVPOKE_SCORE_FALLBACK
    scores = [scorer(col_idx) for col_idx in threat_indices]
    return sum(scores) / len(scores)


def _defensive_threat_score(
    team_indices: Sequence[int],
    pokemon_types_by_row: Sequence[tuple[str, ...]],
    threat_attack_types: tuple[str, ...],
    type_effectiveness: Mapping[str, Mapping[str, float]],
) -> float:
    if not threat_attack_types:
        return NORMALIZED_PVPOKE_SCORE_FALLBACK
    scores = []
    for attack_type in threat_attack_types:
        if attack_type not in type_effectiveness:
            continue
        weak_count = 0
        resist_count = 0
        for row_idx in team_indices:
            multiplier = _type_multiplier(attack_type, pokemon_types_by_row[row_idx], type_effectiveness)
            if multiplier > 1.0:
                weak_count += 1
            elif multiplier < 1.0:
                resist_count += 1
        exposure = weak_count / len(team_indices)
        resistance = resist_count / len(team_indices)
        scores.append(_clamp(0.5 + (0.5 * resistance) - (0.65 * exposure)))
    return sum(scores) / len(scores) if scores else NORMALIZED_PVPOKE_SCORE_FALLBACK


def _offensive_threat_score(
    move_types: Sequence[str],
    defender_types: tuple[str, ...],
    type_effectiveness: Mapping[str, Mapping[str, float]],
) -> float:
    if not defender_types:
        return NORMALIZED_PVPOKE_SCORE_FALLBACK
    best_multiplier = max(
        _type_multiplier(move_type, defender_types, type_effectiveness)
        for move_type in move_types
    )
    return _clamp((best_multiplier - 0.39) / (1.6 - 0.39))


def _overwhelming_loss_count(
    team_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    threat_indices: Sequence[int],
) -> int:
    count = 0
    for col_idx in threat_indices:
        best_score = max(
            max(matrix[row_idx][col_idx] for matrix in matrices)
            for row_idx in team_indices
        )
        if best_score < OVERWHELMING_LOSS_SCORE_THRESHOLD:
            count += 1
    return count


def _shield_fragility(
    team_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    threat_indices: Sequence[int],
) -> float:
    if not matrices or not threat_indices:
        return 0.0
    spreads = []
    for col_idx in threat_indices:
        best_by_shield = [max(matrix[row_idx][col_idx] for row_idx in team_indices) for matrix in matrices]
        spreads.append((max(best_by_shield) - min(best_by_shield)) / 1000.0)
    return _clamp(sum(spreads) / len(spreads))


def _average_indexed_values(
    team_indices: Sequence[int],
    values: Sequence[float] | None,
    fallback: float,
) -> float:
    if not values:
        return fallback
    selected = [values[index] for index in team_indices if index < len(values)]
    return sum(selected) / len(selected) if selected else fallback


def _type_multiplier(
    attack_type: str,
    defender_types: tuple[str, ...],
    type_effectiveness: Mapping[str, Mapping[str, float]],
) -> float:
    multiplier = 1.0
    effectiveness_by_defender = type_effectiveness.get(attack_type, {})
    for defender_type in defender_types:
        defender_multiplier = effectiveness_by_defender.get(defender_type, 1.0)
        if not math.isfinite(defender_multiplier) or defender_multiplier <= 0.0:
            defender_multiplier = 1.0
        multiplier *= defender_multiplier
    return multiplier


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
