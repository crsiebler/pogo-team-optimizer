from __future__ import annotations

import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal


DOMINATING_SCORE_THRESHOLD = 600
OVERWHELMING_LOSS_THRESHOLD = 400
LINEUP_VIABILITY_THRESHOLD = 500.0
ROSTER_LINEUP_TOP_N = 10
LOW_UTILITY_LINEUP_RATE = 0.10
SPECIALIST_LINEUP_RATE = 0.25
FLEXIBLE_LINEUP_RATE = 0.50
BATTLE_FRONTIER_LOW_POINT_MAX = 1
BATTLE_FRONTIER_HIGH_POINT_MIN = 3


BenchUtilityTier = Literal["core", "flexible", "specialist", "low_utility", "unbringable"]
BenchWarningCategory = Literal["bench_utility", "battle_frontier"]
BenchWarningSeverity = Literal["medium", "high"]
LineupShape = Literal["ABC", "ABB", "ABA", "unclassified"]


@dataclass(frozen=True)
class OrderedLineup:
    lead_index: int
    back_indices: tuple[int, int]

    def __post_init__(self) -> None:
        if len(self.back_indices) != 2:
            raise ValueError("back_indices must contain two distinct members")

        canonical_back_indices = tuple(sorted(self.back_indices))
        if canonical_back_indices[0] == canonical_back_indices[1]:
            raise ValueError("back_indices must contain two distinct members")
        if self.lead_index in canonical_back_indices:
            raise ValueError("lead_index must be distinct from back_indices")

        object.__setattr__(self, "back_indices", canonical_back_indices)


@dataclass(frozen=True)
class LineupResourcePath:
    name: str
    lead_shield: int
    back_shield: int


@dataclass(frozen=True)
class LineupPathScore:
    path_name: str
    best_scores: tuple[int, ...]
    dominate_count: int
    overwhelming_count: int
    mean_best_score: float


@dataclass(frozen=True)
class OrderedLineupScore:
    lineup: OrderedLineup
    path_scores: tuple[LineupPathScore, ...]


@dataclass(frozen=True)
class RosterLineupScore:
    objective_score: float
    best_lineup_score: float
    top_lineup_mean: float
    viable_lineup_count: int


@dataclass(frozen=True)
class BattleFrontierLineupUsage:
    viable_lineup_count: int
    free_low_point_usage_rate: float
    high_point_usage_rate: float


@dataclass(frozen=True)
class BenchUtilityWarning:
    category: BenchWarningCategory
    code: str
    severity: BenchWarningSeverity
    message: str


@dataclass(frozen=True)
class RosterMemberLineupUsage:
    member_index: int
    lineups_used: int
    lead_lineups_used: int
    back_lineups_used: int
    viable_lineup_rate: float
    all_lineup_rate: float
    best_lineup_score: float
    tier: BenchUtilityTier
    warnings: tuple[BenchUtilityWarning, ...]


LINEUP_RESOURCE_PATHS = (
    LineupResourcePath(name="balanced", lead_shield=1, back_shield=1),
    LineupResourcePath(name="shield_spend", lead_shield=2, back_shield=0),
    LineupResourcePath(name="shield_save", lead_shield=0, back_shield=2),
)


def enumerate_ordered_lineups(roster_indices: Sequence[int]) -> tuple[OrderedLineup, ...]:
    if len(roster_indices) < 3:
        raise ValueError("roster_indices must contain at least 3 members")
    if len(set(roster_indices)) != len(roster_indices):
        raise ValueError("roster_indices must not contain duplicates")

    lineups: list[OrderedLineup] = []
    for lead_index in roster_indices:
        back_candidates = [index for index in roster_indices if index != lead_index]
        for back_indices in itertools.combinations(back_candidates, 2):
            lineups.append(OrderedLineup(lead_index=lead_index, back_indices=back_indices))
    return tuple(lineups)


def score_ordered_lineup(
    lineup: OrderedLineup,
    matrices: Sequence[Sequence[Sequence[int]]],
) -> OrderedLineupScore:
    path_scores = tuple(_score_resource_path(lineup, matrices, path) for path in LINEUP_RESOURCE_PATHS)
    return OrderedLineupScore(lineup=lineup, path_scores=path_scores)


def score_roster_lineup_depth(
    roster_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    top_n: int = ROSTER_LINEUP_TOP_N,
) -> RosterLineupScore:
    lineup_scores = sorted(
        (_lineup_mean_score(score_ordered_lineup(lineup, matrices)) for lineup in enumerate_ordered_lineups(roster_indices)),
        reverse=True,
    )
    if not lineup_scores:
        return RosterLineupScore(0.0, 0.0, 0.0, 0)

    top_scores = lineup_scores[:top_n]
    best_lineup_score = lineup_scores[0]
    top_lineup_mean = sum(top_scores) / len(top_scores)
    viable_lineup_count = sum(score >= LINEUP_VIABILITY_THRESHOLD for score in lineup_scores)
    viable_lineup_rate = viable_lineup_count / len(lineup_scores)
    objective_score = (
        (0.45 * best_lineup_score)
        + (0.40 * top_lineup_mean)
        + (0.15 * viable_lineup_rate * 100.0)
    )
    return RosterLineupScore(
        objective_score=objective_score,
        best_lineup_score=best_lineup_score,
        top_lineup_mean=top_lineup_mean,
        viable_lineup_count=viable_lineup_count,
    )


def score_roster_bench_utility(
    roster_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    battle_frontier_points_by_row: Sequence[int] | None = None,
) -> tuple[RosterMemberLineupUsage, ...]:
    if len(roster_indices) < 3 or len(matrices) < len(LINEUP_RESOURCE_PATHS):
        return tuple(
            _unused_member_usage(index, battle_frontier_points_by_row)
            for index in roster_indices
        )

    lineups = enumerate_ordered_lineups(roster_indices)
    total_lineups = len(lineups)
    used_counts = dict.fromkeys(roster_indices, 0)
    lead_counts = dict.fromkeys(roster_indices, 0)
    back_counts = dict.fromkeys(roster_indices, 0)
    best_scores = dict.fromkeys(roster_indices, 0.0)
    viable_lineup_count = 0

    for lineup in lineups:
        score = score_ordered_lineup(lineup, matrices)
        lineup_score = _lineup_mean_score(score)
        if lineup_score < LINEUP_VIABILITY_THRESHOLD:
            continue

        viable_lineup_count += 1
        lineup_members = (lineup.lead_index, *lineup.back_indices)
        for member_index in lineup_members:
            used_counts[member_index] += 1
            best_scores[member_index] = max(best_scores[member_index], lineup_score)
        lead_counts[lineup.lead_index] += 1
        for member_index in lineup.back_indices:
            back_counts[member_index] += 1

    return tuple(
        _member_usage(
            member_index=index,
            lineups_used=used_counts[index],
            lead_lineups_used=lead_counts[index],
            back_lineups_used=back_counts[index],
            viable_lineup_count=viable_lineup_count,
            total_lineups=total_lineups,
            best_lineup_score=best_scores[index],
            battle_frontier_points_by_row=battle_frontier_points_by_row,
        )
        for index in roster_indices
    )


def score_battle_frontier_lineup_usage(
    roster_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    points_by_row: Sequence[int],
) -> BattleFrontierLineupUsage:
    if len(roster_indices) < 3 or len(matrices) < len(LINEUP_RESOURCE_PATHS):
        return BattleFrontierLineupUsage(0, 0.0, 0.0)

    viable_lineup_count = 0
    free_low_point_appearances = 0
    high_point_appearances = 0
    for lineup in enumerate_ordered_lineups(roster_indices):
        score = score_ordered_lineup(lineup, matrices)
        if _lineup_mean_score(score) < LINEUP_VIABILITY_THRESHOLD:
            continue

        viable_lineup_count += 1
        for member_index in (lineup.lead_index, *lineup.back_indices):
            points = points_by_row[member_index]
            if points <= BATTLE_FRONTIER_LOW_POINT_MAX:
                free_low_point_appearances += 1
            if points >= BATTLE_FRONTIER_HIGH_POINT_MIN:
                high_point_appearances += 1

    total_appearances = viable_lineup_count * 3
    if total_appearances == 0:
        return BattleFrontierLineupUsage(0, 0.0, 0.0)
    return BattleFrontierLineupUsage(
        viable_lineup_count=viable_lineup_count,
        free_low_point_usage_rate=free_low_point_appearances / total_appearances,
        high_point_usage_rate=high_point_appearances / total_appearances,
    )


def classify_bench_utility(lineups_used: int, viable_lineup_rate: float) -> BenchUtilityTier:
    if lineups_used == 0:
        return "unbringable"
    if viable_lineup_rate < LOW_UTILITY_LINEUP_RATE:
        return "low_utility"
    if viable_lineup_rate < SPECIALIST_LINEUP_RATE:
        return "specialist"
    if viable_lineup_rate < FLEXIBLE_LINEUP_RATE:
        return "flexible"
    return "core"


def classify_lineup_shape(
    lead_types: Sequence[str],
    back_one_types: Sequence[str],
    back_two_types: Sequence[str],
) -> LineupShape:
    lead_type_set = set(lead_types)
    back_one_type_set = set(back_one_types)
    back_two_type_set = set(back_two_types)
    if not lead_type_set or not back_one_type_set or not back_two_type_set:
        return "unclassified"

    lead_back_one_overlap = bool(lead_type_set & back_one_type_set)
    lead_back_two_overlap = bool(lead_type_set & back_two_type_set)
    back_pair_overlap = bool(back_one_type_set & back_two_type_set)

    if not lead_back_one_overlap and not lead_back_two_overlap and not back_pair_overlap:
        return "ABC"
    if back_pair_overlap and not lead_back_one_overlap and not lead_back_two_overlap:
        return "ABB"
    if (lead_back_one_overlap != lead_back_two_overlap) and not back_pair_overlap:
        return "ABA"
    return "unclassified"


def bench_utility_warnings(tier: BenchUtilityTier) -> tuple[BenchUtilityWarning, ...]:
    if tier == "unbringable":
        return (
            BenchUtilityWarning(
                category="bench_utility",
                code="unbringable",
                severity="high",
                message="Roster member appears in no viable ordered lineups.",
            ),
        )
    if tier == "low_utility":
        return (
            BenchUtilityWarning(
                category="bench_utility",
                code="low_usage",
                severity="medium",
                message="Roster member appears in few viable ordered lineups.",
            ),
        )
    return ()


def battle_frontier_bench_warnings(
    tier: BenchUtilityTier,
    points: int,
) -> tuple[BenchUtilityWarning, ...]:
    if tier not in {"low_utility", "unbringable"}:
        return ()

    warnings = []
    if points >= BATTLE_FRONTIER_HIGH_POINT_MIN:
        warnings.append(
            BenchUtilityWarning(
                category="battle_frontier",
                code="expensive_mostly_bench",
                severity="high",
                message="High-point roster member appears in few or no viable ordered lineups.",
            )
        )
    if points <= BATTLE_FRONTIER_LOW_POINT_MAX:
        warnings.append(
            BenchUtilityWarning(
                category="battle_frontier",
                code="low_point_paper_coverage",
                severity="medium",
                message="Free or low-point roster member is rarely bringable in viable ordered lineups.",
            )
        )
    return tuple(warnings)


def _lineup_mean_score(score: OrderedLineupScore) -> float:
    return sum(path.mean_best_score for path in score.path_scores) / len(score.path_scores)


def _unused_member_usage(
    member_index: int,
    battle_frontier_points_by_row: Sequence[int] | None = None,
) -> RosterMemberLineupUsage:
    return _member_usage(
        member_index=member_index,
        lineups_used=0,
        lead_lineups_used=0,
        back_lineups_used=0,
        viable_lineup_count=0,
        total_lineups=0,
        best_lineup_score=0.0,
        battle_frontier_points_by_row=battle_frontier_points_by_row,
    )


def _member_usage(
    *,
    member_index: int,
    lineups_used: int,
    lead_lineups_used: int,
    back_lineups_used: int,
    viable_lineup_count: int,
    total_lineups: int,
    best_lineup_score: float,
    battle_frontier_points_by_row: Sequence[int] | None = None,
) -> RosterMemberLineupUsage:
    viable_lineup_rate = lineups_used / viable_lineup_count if viable_lineup_count else 0.0
    all_lineup_rate = lineups_used / total_lineups if total_lineups else 0.0
    tier = classify_bench_utility(lineups_used, viable_lineup_rate)
    warnings = bench_utility_warnings(tier)
    if battle_frontier_points_by_row is not None:
        warnings = warnings + battle_frontier_bench_warnings(
            tier,
            battle_frontier_points_by_row[member_index],
        )
    return RosterMemberLineupUsage(
        member_index=member_index,
        lineups_used=lineups_used,
        lead_lineups_used=lead_lineups_used,
        back_lineups_used=back_lineups_used,
        viable_lineup_rate=viable_lineup_rate,
        all_lineup_rate=all_lineup_rate,
        best_lineup_score=best_lineup_score,
        tier=tier,
        warnings=warnings,
    )


def _score_resource_path(
    lineup: OrderedLineup,
    matrices: Sequence[Sequence[Sequence[int]]],
    path: LineupResourcePath,
) -> LineupPathScore:
    lead_scores = matrices[path.lead_shield][lineup.lead_index]
    back_1_scores = matrices[path.back_shield][lineup.back_indices[0]]
    back_2_scores = matrices[path.back_shield][lineup.back_indices[1]]
    best_scores = tuple(
        max(lead_score, back_1_score, back_2_score)
        for lead_score, back_1_score, back_2_score in zip(
            lead_scores, back_1_scores, back_2_scores, strict=True
        )
    )
    dominate_count = sum(score > DOMINATING_SCORE_THRESHOLD for score in best_scores)
    overwhelming_count = sum(score < OVERWHELMING_LOSS_THRESHOLD for score in best_scores)
    mean_best_score = sum(best_scores) / len(best_scores) if best_scores else 0.0
    return LineupPathScore(
        path_name=path.name,
        best_scores=best_scores,
        dominate_count=dominate_count,
        overwhelming_count=overwhelming_count,
        mean_best_score=mean_best_score,
    )
