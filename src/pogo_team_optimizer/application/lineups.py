from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pogo_team_optimizer.domain.models import RankingCategory, RankingProfile

DOMINATING_SCORE_THRESHOLD = 600
OVERWHELMING_LOSS_THRESHOLD = 400
LINEUP_VIABILITY_THRESHOLD = 500.0
ROSTER_LINEUP_TOP_N = 10
LOW_UTILITY_LINEUP_RATE = 0.10
SPECIALIST_LINEUP_RATE = 0.25
FLEXIBLE_LINEUP_RATE = 0.50
BATTLE_FRONTIER_LOW_POINT_MAX = 1
BATTLE_FRONTIER_HIGH_POINT_MIN = 3
LINEUP_RESOURCE_SCORE_WEIGHT = 0.97
LINEUP_ROLE_FIT_SCORE_WEIGHT = 0.03
LINEUP_RESOURCE_WITHOUT_ROLE_SYNERGY_SCORE_WEIGHT = 0.93
LINEUP_RESOURCE_WITH_SYNERGY_SCORE_WEIGHT = 0.90
LINEUP_SYNERGY_SCORE_WEIGHT = 0.07
NORMALIZED_ROLE_FIT_FALLBACK = 0.5


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
class LineupRoleFitScore:
    score: float
    components: dict[str, float]


@dataclass(frozen=True)
class LineupSynergyScore:
    score: float
    components: dict[str, float | str]


@dataclass(frozen=True)
class OrderedLineupScore:
    lineup: OrderedLineup
    path_scores: tuple[LineupPathScore, ...]
    resource_mean_score: float
    role_fit_score: float | None = None
    synergy_score: float | None = None
    lineup_score: float | None = None


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
    species_by_row: Sequence[str] | None = None,
    ranking_profile: RankingProfile | None = None,
    pokemon_types_by_row: Sequence[tuple[str, ...]] | None = None,
    type_effectiveness: dict[str, dict[str, float]] | None = None,
    threat_weights: Sequence[float] | None = None,
) -> OrderedLineupScore:
    path_scores = tuple(
        _score_resource_path(lineup, matrices, path) for path in LINEUP_RESOURCE_PATHS
    )
    resource_mean_score = _mean_path_score(path_scores)
    role_fit_score = None
    synergy_score = None
    lineup_score = resource_mean_score
    if species_by_row is not None and ranking_profile is not None:
        role_fit = calculate_lineup_role_fit(lineup, species_by_row, ranking_profile)
        role_fit_score = role_fit.score
        lineup_score = (
            LINEUP_RESOURCE_SCORE_WEIGHT * resource_mean_score
            + LINEUP_ROLE_FIT_SCORE_WEIGHT * role_fit.score * 1000.0
        )
    if (
        pokemon_types_by_row is not None
        and type_effectiveness
        and all(pokemon_types_by_row[index] for index in (lineup.lead_index, *lineup.back_indices))
        and _has_complete_type_effectiveness(
            tuple(
                pokemon_types_by_row[index] for index in (lineup.lead_index, *lineup.back_indices)
            ),
            type_effectiveness,
        )
    ):
        synergy = calculate_lineup_synergy(
            lineup,
            matrices,
            pokemon_types_by_row,
            type_effectiveness,
            threat_weights=threat_weights,
        )
        synergy_score = synergy.score
        role_component = (
            LINEUP_ROLE_FIT_SCORE_WEIGHT * role_fit_score * 1000.0
            if role_fit_score is not None
            else 0.0
        )
        resource_weight = (
            LINEUP_RESOURCE_WITH_SYNERGY_SCORE_WEIGHT
            if role_fit_score is not None
            else LINEUP_RESOURCE_WITHOUT_ROLE_SYNERGY_SCORE_WEIGHT
        )
        lineup_score = (
            resource_weight * resource_mean_score
            + role_component
            + LINEUP_SYNERGY_SCORE_WEIGHT * synergy.score * 1000.0
        )
    return OrderedLineupScore(
        lineup=lineup,
        path_scores=path_scores,
        resource_mean_score=resource_mean_score,
        role_fit_score=role_fit_score,
        synergy_score=synergy_score,
        lineup_score=lineup_score,
    )


def calculate_lineup_role_fit(
    lineup: OrderedLineup,
    species_by_row: Sequence[str],
    ranking_profile: RankingProfile,
) -> LineupRoleFitScore:
    lead_species = species_by_row[lineup.lead_index]
    back_species = (species_by_row[lineup.back_indices[0]], species_by_row[lineup.back_indices[1]])
    components = {
        "lead_leads": _normalized_role_score(ranking_profile, RankingCategory.LEADS, lead_species),
        "back_switches": _average_back_role_score(
            ranking_profile,
            RankingCategory.SWITCHES,
            back_species,
        ),
        "back_closers": _average_back_role_score(
            ranking_profile,
            RankingCategory.CLOSERS,
            back_species,
        ),
        "back_attackers": _average_back_role_score(
            ranking_profile,
            RankingCategory.ATTACKERS,
            back_species,
        ),
        "back_chargers": _average_back_role_score(
            ranking_profile,
            RankingCategory.CHARGERS,
            back_species,
        ),
        "back_consistency": _average_back_role_score(
            ranking_profile,
            RankingCategory.CONSISTENCY,
            back_species,
        ),
    }
    score = (
        0.375 * components["lead_leads"]
        + 0.250 * components["back_switches"]
        + 0.175 * components["back_closers"]
        + 0.075 * components["back_attackers"]
        + 0.050 * components["back_chargers"]
        + 0.075 * components["back_consistency"]
    )
    return LineupRoleFitScore(score=score, components=components)


def calculate_lineup_synergy(
    lineup: OrderedLineup,
    matrices: Sequence[Sequence[Sequence[int]]],
    pokemon_types_by_row: Sequence[tuple[str, ...]],
    type_effectiveness: dict[str, dict[str, float]],
    threat_weights: Sequence[float] | None = None,
) -> LineupSynergyScore:
    member_indices = (lineup.lead_index, *lineup.back_indices)
    member_types = tuple(pokemon_types_by_row[index] for index in member_indices)
    shape = classify_lineup_shape(*member_types)
    weakness_sets = (
        _weakness_types(member_types[0], type_effectiveness),
        _weakness_types(member_types[1], type_effectiveness),
        _weakness_types(member_types[2], type_effectiveness),
    )
    resistance_sets = (
        _resistance_types(member_types[0], type_effectiveness),
        _resistance_types(member_types[1], type_effectiveness),
        _resistance_types(member_types[2], type_effectiveness),
    )
    shared_weakness_pressure = _shared_weakness_pressure(weakness_sets, type_effectiveness)
    winner_diversity = _winner_diversity(lineup, matrices, threat_weights)
    redundant_coverage = _redundant_coverage(lineup, matrices, threat_weights)
    components: dict[str, float | str] = {
        "shape": shape,
        "shared_weakness_pressure": shared_weakness_pressure,
        "winner_diversity": winner_diversity,
        "redundant_coverage": redundant_coverage,
        "singleton_covers_pair_weakness": 0.0,
        "pair_covers_singleton_weakness": 0.0,
        "unsafe_aba_shared_weakness": 0.0,
        "aba_redundant_strength": 0.0,
    }

    low_shared_weakness = 1.0 - shared_weakness_pressure
    if shape == "ABC":
        score = (
            0.40
            + (0.30 * low_shared_weakness)
            + (0.25 * winner_diversity)
            + (0.05 * redundant_coverage)
        )
    elif shape == "ABB":
        pair_weakness = weakness_sets[1] & weakness_sets[2]
        singleton_weakness = weakness_sets[0]
        singleton_covers_pair = _coverage_rate(pair_weakness, resistance_sets[0])
        pair_covers_singleton = _coverage_rate(
            singleton_weakness,
            resistance_sets[1] | resistance_sets[2],
        )
        components["singleton_covers_pair_weakness"] = singleton_covers_pair
        components["pair_covers_singleton_weakness"] = pair_covers_singleton
        score = (
            0.40
            + (0.30 * singleton_covers_pair)
            + (0.15 * pair_covers_singleton)
            + (0.10 * redundant_coverage)
            + (0.05 * low_shared_weakness)
        )
    elif shape == "ABA":
        shared_back_position = 1 if set(member_types[0]) & set(member_types[1]) else 2
        different_position = 2 if shared_back_position == 1 else 1
        shared_weakness = weakness_sets[0] & weakness_sets[shared_back_position]
        different_resistances = resistance_sets[different_position]
        different_covers_shared_weakness = _coverage_rate(shared_weakness, different_resistances)
        uncovered_shared_weakness = (
            1.0 - different_covers_shared_weakness if shared_weakness else 0.0
        )
        only_different_answer_rate = _only_member_answer_rate(
            lineup,
            matrices,
            member_position=different_position,
            threat_weights=threat_weights,
        )
        unsafe_aba = (0.60 * uncovered_shared_weakness) + (
            0.40 * different_covers_shared_weakness * only_different_answer_rate
        )
        redundant_strength = _shared_member_answer_rate(
            lineup,
            matrices,
            member_positions=(0, shared_back_position),
            threat_weights=threat_weights,
        )
        components["unsafe_aba_shared_weakness"] = unsafe_aba
        components["aba_redundant_strength"] = redundant_strength
        score = (
            0.45 + (0.30 * redundant_strength) + (0.10 * low_shared_weakness) - (0.35 * unsafe_aba)
        )
    else:
        score = (
            0.45
            + (0.20 * low_shared_weakness)
            + (0.20 * winner_diversity)
            + (0.15 * redundant_coverage)
        )

    return LineupSynergyScore(score=_clamp(score), components=components)


def score_roster_lineup_depth(
    roster_indices: Sequence[int],
    matrices: Sequence[Sequence[Sequence[int]]],
    top_n: int = ROSTER_LINEUP_TOP_N,
) -> RosterLineupScore:
    lineup_scores = sorted(
        (
            _lineup_mean_score(score_ordered_lineup(lineup, matrices))
            for lineup in enumerate_ordered_lineups(roster_indices)
        ),
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
        (0.45 * best_lineup_score) + (0.40 * top_lineup_mean) + (0.15 * viable_lineup_rate * 100.0)
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
    pokemon_types_by_row: Sequence[tuple[str, ...]] | None = None,
    type_effectiveness: dict[str, dict[str, float]] | None = None,
    threat_weights: Sequence[float] | None = None,
) -> tuple[RosterMemberLineupUsage, ...]:
    if len(roster_indices) < 3 or len(matrices) < len(LINEUP_RESOURCE_PATHS):
        return tuple(
            _unused_member_usage(index, battle_frontier_points_by_row) for index in roster_indices
        )

    lineups = enumerate_ordered_lineups(roster_indices)
    total_lineups = len(lineups)
    used_counts = dict.fromkeys(roster_indices, 0)
    lead_counts = dict.fromkeys(roster_indices, 0)
    back_counts = dict.fromkeys(roster_indices, 0)
    best_scores = dict.fromkeys(roster_indices, 0.0)
    viable_lineup_count = 0

    for lineup in lineups:
        score = score_ordered_lineup(
            lineup,
            matrices,
            pokemon_types_by_row=pokemon_types_by_row,
            type_effectiveness=type_effectiveness,
            threat_weights=threat_weights,
        )
        lineup_score = _lineup_mean_score(score)
        if (
            score.resource_mean_score < LINEUP_VIABILITY_THRESHOLD
            or lineup_score < LINEUP_VIABILITY_THRESHOLD
        ):
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
    pokemon_types_by_row: Sequence[tuple[str, ...]] | None = None,
    type_effectiveness: dict[str, dict[str, float]] | None = None,
    threat_weights: Sequence[float] | None = None,
) -> BattleFrontierLineupUsage:
    if len(roster_indices) < 3 or len(matrices) < len(LINEUP_RESOURCE_PATHS):
        return BattleFrontierLineupUsage(0, 0.0, 0.0)

    viable_lineup_count = 0
    free_low_point_appearances = 0
    high_point_appearances = 0
    for lineup in enumerate_ordered_lineups(roster_indices):
        score = score_ordered_lineup(
            lineup,
            matrices,
            pokemon_types_by_row=pokemon_types_by_row,
            type_effectiveness=type_effectiveness,
            threat_weights=threat_weights,
        )
        lineup_score = _lineup_mean_score(score)
        if (
            score.resource_mean_score < LINEUP_VIABILITY_THRESHOLD
            or lineup_score < LINEUP_VIABILITY_THRESHOLD
        ):
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
    if score.lineup_score is not None:
        return score.lineup_score
    return score.resource_mean_score


def _mean_path_score(path_scores: Sequence[LineupPathScore]) -> float:
    return sum(path.mean_best_score for path in path_scores) / len(path_scores)


def _average_back_role_score(
    ranking_profile: RankingProfile,
    category: RankingCategory,
    species_names: tuple[str, str],
) -> float:
    return sum(
        _normalized_role_score(ranking_profile, category, species_name)
        for species_name in species_names
    ) / len(species_names)


def _normalized_role_score(
    ranking_profile: RankingProfile,
    category: RankingCategory,
    species_name: str,
) -> float:
    row = ranking_profile.scores_by_category.get(category, {}).get(species_name)
    if row is None or row.normalized_score is None:
        return NORMALIZED_ROLE_FIT_FALLBACK
    return row.normalized_score


def _has_complete_type_effectiveness(
    member_types: tuple[tuple[str, ...], ...],
    type_effectiveness: dict[str, dict[str, float]],
) -> bool:
    defender_types = {defender_type for types in member_types for defender_type in types}
    if not defender_types:
        return False
    if not defender_types <= set(type_effectiveness):
        return False
    for effectiveness_by_defender in type_effectiveness.values():
        for defender_type in defender_types:
            multiplier = effectiveness_by_defender.get(defender_type)
            if multiplier is None or not math.isfinite(multiplier):
                return False
    return True


def _weakness_types(
    defender_types: tuple[str, ...],
    type_effectiveness: dict[str, dict[str, float]],
) -> set[str]:
    return {
        attack_type
        for attack_type in type_effectiveness
        if _defensive_multiplier(attack_type, defender_types, type_effectiveness) > 1.0
    }


def _resistance_types(
    defender_types: tuple[str, ...],
    type_effectiveness: dict[str, dict[str, float]],
) -> set[str]:
    return {
        attack_type
        for attack_type in type_effectiveness
        if _defensive_multiplier(attack_type, defender_types, type_effectiveness) < 1.0
    }


def _defensive_multiplier(
    attack_type: str,
    defender_types: tuple[str, ...],
    type_effectiveness: dict[str, dict[str, float]],
) -> float:
    multiplier = 1.0
    effectiveness_by_defender = type_effectiveness.get(attack_type, {})
    for defender_type in defender_types:
        multiplier *= effectiveness_by_defender.get(defender_type, 1.0)
    return multiplier


def _shared_weakness_pressure(
    weakness_sets: tuple[set[str], set[str], set[str]],
    type_effectiveness: dict[str, dict[str, float]],
) -> float:
    if not type_effectiveness:
        return 0.0
    shared_pairs = 0
    for attack_type in type_effectiveness:
        weak_count = sum(attack_type in weaknesses for weaknesses in weakness_sets)
        if weak_count >= 2:
            shared_pairs += weak_count - 1
    return min(1.0, shared_pairs / (len(type_effectiveness) * 2))


def _coverage_rate(threat_types: set[str], answer_types: set[str]) -> float:
    if not threat_types:
        return 0.0
    return len(threat_types & answer_types) / len(threat_types)


def _winner_diversity(
    lineup: OrderedLineup,
    matrices: Sequence[Sequence[Sequence[int]]],
    threat_weights: Sequence[float] | None,
) -> float:
    winner_weights = [0.0, 0.0, 0.0]
    for column_index, weight in enumerate(_normalized_threat_weights(matrices, threat_weights)):
        member_scores = _member_column_scores(lineup, matrices, column_index)
        best_score = max(member_scores)
        if best_score <= 500:
            continue
        for position, score in enumerate(member_scores):
            if score == best_score:
                winner_weights[position] += weight
                break
    active_winners = sum(weight > 0.0 for weight in winner_weights)
    return active_winners / 3


def _redundant_coverage(
    lineup: OrderedLineup,
    matrices: Sequence[Sequence[Sequence[int]]],
    threat_weights: Sequence[float] | None,
) -> float:
    coverage = 0.0
    for column_index, weight in enumerate(_normalized_threat_weights(matrices, threat_weights)):
        member_scores = _member_column_scores(lineup, matrices, column_index)
        if sum(score > 500 for score in member_scores) >= 2:
            coverage += weight
    return coverage


def _only_member_answer_rate(
    lineup: OrderedLineup,
    matrices: Sequence[Sequence[Sequence[int]]],
    member_position: int,
    threat_weights: Sequence[float] | None,
) -> float:
    rate = 0.0
    for column_index, weight in enumerate(_normalized_threat_weights(matrices, threat_weights)):
        member_scores = _member_column_scores(lineup, matrices, column_index)
        if (
            member_scores[member_position] > 500
            and sum(score > 500 for score in member_scores) == 1
        ):
            rate += weight
    return rate


def _shared_member_answer_rate(
    lineup: OrderedLineup,
    matrices: Sequence[Sequence[Sequence[int]]],
    member_positions: tuple[int, int],
    threat_weights: Sequence[float] | None,
) -> float:
    rate = 0.0
    for column_index, weight in enumerate(_normalized_threat_weights(matrices, threat_weights)):
        member_scores = _member_column_scores(lineup, matrices, column_index)
        if all(member_scores[position] > 500 for position in member_positions):
            rate += weight
    return rate


def _member_column_scores(
    lineup: OrderedLineup,
    matrices: Sequence[Sequence[Sequence[int]]],
    column_index: int,
) -> tuple[float, float, float]:
    member_indices = (lineup.lead_index, *lineup.back_indices)
    return (
        float(max(matrix[member_indices[0]][column_index] for matrix in matrices)),
        float(max(matrix[member_indices[1]][column_index] for matrix in matrices)),
        float(max(matrix[member_indices[2]][column_index] for matrix in matrices)),
    )


def _normalized_threat_weights(
    matrices: Sequence[Sequence[Sequence[int]]],
    threat_weights: Sequence[float] | None,
) -> tuple[float, ...]:
    col_count = len(matrices[0][0]) if matrices and matrices[0] else 0
    if col_count == 0:
        return ()
    if threat_weights is None:
        return tuple(1.0 / col_count for _ in range(col_count))
    weights = tuple(float(weight) for weight in threat_weights[:col_count])
    if len(weights) != col_count or sum(weights) <= 0.0:
        return tuple(1.0 / col_count for _ in range(col_count))
    total_weight = sum(weights)
    return tuple(weight / total_weight for weight in weights)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


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
