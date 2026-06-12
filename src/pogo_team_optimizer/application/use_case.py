from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any

from pogo_team_optimizer.application.analyzers import (
    build_target_map,
    build_threats,
    coverage_by_shield,
    to_team_members,
)
from pogo_team_optimizer.application.lineups import (
    LINEUP_RESOURCE_PATHS,
    LINEUP_RESOURCE_SCORE_WEIGHT,
    LINEUP_RESOURCE_WITHOUT_ROLE_SYNERGY_SCORE_WEIGHT,
    LINEUP_RESOURCE_WITH_SYNERGY_SCORE_WEIGHT,
    LINEUP_ROLE_FIT_SCORE_WEIGHT,
    LINEUP_SYNERGY_SCORE_WEIGHT,
    LINEUP_VIABILITY_THRESHOLD,
    classify_lineup_shape,
    enumerate_ordered_lineups,
    score_battle_frontier_lineup_usage,
    score_roster_bench_utility,
    score_ordered_lineup,
)
from pogo_team_optimizer.application.normalization import parse_species
from pogo_team_optimizer.application.optimizer import TeamOptimizer
from pogo_team_optimizer.application.ranking_pools import build_ranking_pools
from pogo_team_optimizer.application.scoring import (
    PvPokeScoreNormalizationPolicy,
    RosterScore,
    WeightedScoreComponent,
    calculate_ranking_aware_roster_score,
)
from pogo_team_optimizer.domain.interfaces import (
    BattleFrontierPointsRepository,
    MatchupValue,
    MoveRepository,
    PokemonRepository,
    RankingsRepository,
    SimulationMatrixRepository,
    SwitchRankingsRepository,
    TypeEffectivenessRepository,
)
from pogo_team_optimizer.domain.models import RankingCategory, RankingProfile


MAX_RECOMMENDED_LINEUPS = 5
LOGGER = logging.getLogger(__name__)


class AnalyzeMetaUseCase:
    def __init__(
        self,
        simulation_repository: SimulationMatrixRepository,
        pokemon_repository: PokemonRepository,
        switch_rankings_repository: SwitchRankingsRepository | None = None,
        battle_frontier_points_repository: BattleFrontierPointsRepository | None = None,
        move_repository: MoveRepository | None = None,
        type_effectiveness_repository: TypeEffectivenessRepository | None = None,
        rankings_repository: RankingsRepository | None = None,
    ) -> None:
        self.simulation_repository = simulation_repository
        self.pokemon_repository = pokemon_repository
        self.switch_rankings_repository = switch_rankings_repository
        self.battle_frontier_points_repository = battle_frontier_points_repository
        self.move_repository = move_repository
        self.type_effectiveness_repository = type_effectiveness_repository
        self.rankings_repository = rankings_repository

    def execute(
        self,
        top_threats: int = 10,
        top_lineups: int = MAX_RECOMMENDED_LINEUPS,
        seed: int = 7,
        restarts: int = 250,
        workers: int = 1,
        safety_priority: str = "medium",
    ) -> dict[str, Any]:
        LOGGER.info("loading simulation matrices")
        loaded_row_labels, col_labels, loaded_matrices = self.simulation_repository.load()
        ranking_profile = self._load_normalized_ranking_profile()
        row_labels, matrices = _filter_complete_candidate_rows(
            loaded_row_labels,
            loaded_matrices,
            ranking_profile,
        )
        LOGGER.info(
            "loaded matrices rows=%s eligible_rows=%s cols=%s shields=%s",
            len(loaded_row_labels),
            len(row_labels),
            len(col_labels),
            len(matrices),
        )
        col_species = [parse_species(label) for label in col_labels]
        species_groups: dict[str, list[int]] = defaultdict(list)
        for col_idx, species in enumerate(col_species):
            species_groups[species].append(col_idx)
        weights = [0.0] * len(col_labels)
        group_count = len(species_groups)
        for indices in species_groups.values():
            weight = 1.0 / group_count / len(indices)
            for col_idx in indices:
                weights[col_idx] = weight

        species_cache = {
            parse_species(label): self.pokemon_repository.get_types(parse_species(label))
            for label in row_labels
        }
        row_species = [parse_species(label) for label in row_labels]
        pokemon_types_by_row = [species_cache[parse_species(label)] for label in row_labels]
        opponent_types_by_col = [self._types_for_label(label) for label in col_labels]
        move_types_by_row = [self._move_types_for_label(label) for label in row_labels]
        type_effectiveness = (
            self.type_effectiveness_repository.load()
            if self.type_effectiveness_repository is not None
            else {}
        )

        bulk_by_row: list[float] = []
        safety_by_row: list[float] = []
        LOGGER.info("building bulk and safety inputs rows=%s", len(row_labels))
        for label in row_labels:
            species = parse_species(label)
            stats = self.pokemon_repository.get_base_stats(species)
            switch_score = 60.0
            if self.switch_rankings_repository is not None:
                ranked_score = self.switch_rankings_repository.get_switch_score(species)
                if ranked_score is not None:
                    switch_score = ranked_score
            safety_by_row.append(switch_score)
            if stats is None:
                bulk_by_row.append(0.0)
                continue
            atk, defense, hp = stats
            if atk <= 0:
                bulk_by_row.append(0.0)
                continue
            bulk_by_row.append((defense * hp) / atk)

        battle_frontier_points_by_row: list[int] | None = None
        if self.battle_frontier_points_repository is not None:
            LOGGER.info("building Battle Frontier point inputs")
            battle_frontier_points_by_row = [
                self.battle_frontier_points_repository.get_points(parse_species(label))
                for label in row_labels
            ]

        consistency_by_row = _normalized_category_scores_by_row(
            row_species,
            ranking_profile,
            RankingCategory.CONSISTENCY,
        )
        ranking_pools = build_ranking_pools(
            active_profile=ranking_profile,
            full_meta_profile=None,
            row_labels=row_labels,
            col_labels=col_labels,
            top_threat_count=top_threats,
        )
        top_threat_indices = [entry.matrix_index for entry in ranking_pools.top_threats]

        safety_priority_rules: dict[str, tuple[float | None, int, float]] = {
            "low": (72.0, 0, 90.0),
            "medium": (78.0, 1, 90.0),
            "high": (82.0, 2, 90.0),
        }
        if safety_priority not in safety_priority_rules:
            raise ValueError(
                "Invalid safety priority "
                f"'{safety_priority}'. Expected one of: {', '.join(sorted(safety_priority_rules))}"
            )
        safety_floor, min_safe_members, safe_member_floor = safety_priority_rules[safety_priority]

        optimizer = TeamOptimizer(
            row_labels,
            col_labels,
            matrices,
            bulk_by_row=bulk_by_row,
            safety_by_row=safety_by_row,
            consistency_by_row=consistency_by_row,
            pokemon_types_by_row=pokemon_types_by_row,
            opponent_types_by_col=opponent_types_by_col,
            move_types_by_row=move_types_by_row,
            type_effectiveness=type_effectiveness,
            top_threat_indices=top_threat_indices,
            full_meta_indices=list(range(len(col_labels))),
            battle_frontier_points_by_row=battle_frontier_points_by_row,
            seed=seed,
        )
        LOGGER.info("starting optimizer restarts=%s safety_priority=%s", restarts, safety_priority)
        best_team = optimizer.optimize(
            restarts=restarts,
            safety_floor=safety_floor,
            min_safe_members=min_safe_members,
            safe_member_floor=safe_member_floor,
            workers=workers,
        )
        LOGGER.info("optimizer complete team=%s", ",".join(str(idx) for idx in best_team.member_indices))

        total_pairs = len(col_labels) * len(matrices)
        score = best_team.score
        dominate_count = int(score[11])
        overwhelming_count = int(-score[12])
        single_cover_pairs = int(-score[3])
        no_cover_pairs = int(-score[2])
        metrics = {
            "pair_coverage": int(score[0]),
            "full_col_coverage": int(score[1]),
            "redundant_coverage_2plus": int(score[8]),
            "redundant_coverage_3plus": int(score[9]),
            "single_cover_pairs": single_cover_pairs,
            "single_cover_rate": single_cover_pairs / total_pairs,
            "no_cover_pairs": no_cover_pairs,
            "no_cover_rate": no_cover_pairs / total_pairs,
            "bulk_score": float(score[5]),
            "safety_score": float(score[6]),
            "consistency_score": float(score[7]),
            "weighted_worst_best_score": float(score[4]),
            "mean_best_score": float(score[10]),
            "dominate_count": dominate_count,
            "dominate_rate": dominate_count / total_pairs,
            "overwhelming_count": overwhelming_count,
            "overwhelming_rate": overwhelming_count / total_pairs,
            "total_pairs": total_pairs,
            "bulk_pool_min": min(bulk_by_row) if bulk_by_row else 0.0,
            "bulk_pool_max": max(bulk_by_row) if bulk_by_row else 0.0,
            "bulk_pool_mean": (sum(bulk_by_row) / len(bulk_by_row)) if bulk_by_row else 0.0,
            "safety_pool_min": min(safety_by_row) if safety_by_row else 60.0,
            "safety_pool_max": max(safety_by_row) if safety_by_row else 60.0,
            "safety_pool_mean": (sum(safety_by_row) / len(safety_by_row))
            if safety_by_row
            else 60.0,
            "safety_priority": safety_priority,
            "safety_floor_target": safety_floor if safety_floor is not None else 0.0,
            "safe_member_floor": safe_member_floor,
            "safe_member_target": min_safe_members,
            "lineup_objective_score": float(score[13]),
            "lineup_best_score": float(score[14]),
            "lineup_top_n_mean_score": float(score[15]),
            "lineup_viable_count": int(score[16]),
            "defensive_type_score": float(score[17]),
            "offensive_move_score": float(score[18]),
            "ranking_aware_score": float(score[19]),
            "legacy_full_roster_mean_best_score": float(score[10]),
            "legacy_full_roster_dominate_count": dominate_count,
            "legacy_full_roster_overwhelming_count": overwhelming_count,
        }
        if battle_frontier_points_by_row is not None:
            battle_frontier_team_points = [
                battle_frontier_points_by_row[idx] for idx in best_team.member_indices
            ]
            battle_frontier_lineup_usage = score_battle_frontier_lineup_usage(
                best_team.member_indices,
                matrices,
                battle_frontier_points_by_row,
                pokemon_types_by_row=pokemon_types_by_row,
                type_effectiveness=type_effectiveness,
                threat_weights=weights,
            )
            metrics.update(
                {
                    "battle_frontier_points_used": sum(battle_frontier_team_points),
                    "battle_frontier_five_point_members": sum(
                        points == 5 for points in battle_frontier_team_points
                    ),
                    "battle_frontier_mega_members": sum(
                        "(Mega" in row_labels[idx] for idx in best_team.member_indices
                    ),
                    "battle_frontier_max_points": optimizer.battle_frontier_max_points,
                    "battle_frontier_max_five_point_members": (
                        optimizer.battle_frontier_max_five_point_members
                    ),
                    "battle_frontier_max_mega_members": optimizer.battle_frontier_max_mega_members,
                    "battle_frontier_free_low_point_usage_rate": (
                        battle_frontier_lineup_usage.free_low_point_usage_rate
                    ),
                    "battle_frontier_high_point_usage_rate": (
                        battle_frontier_lineup_usage.high_point_usage_rate
                    ),
                }
            )

        LOGGER.info("assembling lineup diagnostics")
        recommended_lineups = _build_recommended_lineups(
            row_labels=row_labels,
            matrices=matrices,
            team_indices=best_team.member_indices,
            species_cache=species_cache,
            ranking_profile=ranking_profile,
            species_by_row=row_species,
            pokemon_types_by_row=pokemon_types_by_row,
            type_effectiveness=type_effectiveness,
            threat_weights=weights,
            battle_frontier_points_by_row=battle_frontier_points_by_row,
            limit=top_lineups,
        )
        roster_score = calculate_ranking_aware_roster_score(
            team_indices=best_team.member_indices,
            matrices=matrices,
            bulk_by_row=bulk_by_row,
            safety_by_row=safety_by_row,
            consistency_by_row=consistency_by_row,
            pokemon_types_by_row=pokemon_types_by_row,
            move_types_by_row=move_types_by_row,
            opponent_types_by_col=opponent_types_by_col,
            type_effectiveness=type_effectiveness,
            top_threat_indices=top_threat_indices,
            full_meta_indices=list(range(len(col_labels))),
        )
        bench_utility = _build_actionable_bench_utility(
            row_labels=row_labels,
            matrices=matrices,
            team_indices=best_team.member_indices,
            species_cache=species_cache,
            battle_frontier_points_by_row=battle_frontier_points_by_row,
            pokemon_types_by_row=pokemon_types_by_row,
            type_effectiveness=type_effectiveness,
            threat_weights=weights,
        )
        threats = build_threats(
            row_labels,
            col_labels,
            matrices,
            best_team.member_indices,
            top_n=top_threats,
        )

        LOGGER.info("assembling result payload")
        result = {
            "recommended_team": {
                "members": to_team_members(best_team.member_indices, row_labels, species_cache),
                "score": best_team.score,
                "bulk_score": sum(bulk_by_row[idx] for idx in best_team.member_indices)
                / len(best_team.member_indices),
                "safety_score": sum(safety_by_row[idx] for idx in best_team.member_indices)
                / len(best_team.member_indices),
                "metrics": metrics,
                "score_breakdown": _roster_score_breakdown_payload(roster_score),
                "ranking_diagnostics": _build_ranking_diagnostics(
                    row_labels=row_labels,
                    col_labels=col_labels,
                    matrices=matrices,
                    metrics=metrics,
                    team_indices=best_team.member_indices,
                    pokemon_types_by_row=pokemon_types_by_row,
                    type_effectiveness=type_effectiveness,
                    ranking_profile=ranking_profile,
                ),
                "bench_utility": bench_utility,
                "shadow_count": sum(
                    1 for idx in best_team.member_indices if "(Shadow)" in row_labels[idx]
                ),
            },
            "coverage": coverage_by_shield(matrices, best_team.member_indices, weights),
            "threats": threats,
            "safe_cores": [],
            "target_map": build_target_map(
                row_labels, col_labels, matrices, best_team.member_indices
            ),
            "recommended_lineups": recommended_lineups,
        }
        LOGGER.info(
            "result payload complete recommended_lineups=%s bench_utility=%s threats=%s",
            len(recommended_lineups),
            len(bench_utility),
            len(result["threats"]),
        )
        return result

    def _load_normalized_ranking_profile(self) -> RankingProfile | None:
        if self.rankings_repository is None:
            return None
        return PvPokeScoreNormalizationPolicy().normalize_profile(self.rankings_repository.load())

    def _move_types_for_label(self, label: str) -> tuple[str, ...]:
        if self.move_repository is None:
            return tuple()

        match = re.search(
            r"\s+(?P<fast>[A-Za-z0-9]+)\+(?P<charged_one>[A-Za-z0-9]+)/"
            r"(?P<charged_two>[A-Za-z0-9]+)(?:\s+\d+/\d+/\d+)?$",
            label,
        )
        if match is None:
            return tuple()

        move_types = []
        for token in ("fast", "charged_one", "charged_two"):
            move_type = self.move_repository.get_move_type(match.group(token))
            if move_type is not None:
                move_types.append(move_type)
        return tuple(move_types)

    def _types_for_label(self, label: str) -> tuple[str, ...]:
        try:
            return self.pokemon_repository.get_types(parse_species(label))
        except KeyError:
            return tuple()


def _filter_complete_candidate_rows(
    row_labels: list[str],
    matrices: list[list[list[MatchupValue]]],
    ranking_profile: RankingProfile | None = None,
) -> tuple[list[str], list[list[list[int]]]]:
    overall_ranking_species = _active_overall_ranking_species(ranking_profile)
    eligible_indices = [
        row_idx
        for row_idx in range(len(row_labels))
        if _row_has_complete_matchups(row_idx, matrices)
        and (
            overall_ranking_species is None
            or parse_species(row_labels[row_idx]) in overall_ranking_species
        )
    ]
    if len(eligible_indices) < 6:
        raise ValueError(
            f"Only {len(eligible_indices)} eligible candidates remain after filtering rows "
            "with missing matchup data from configured shield matrices"
            f"{_ranking_filter_reason(overall_ranking_species)}; "
            f"at least 6 are required from {len(row_labels)} loaded candidates."
        )

    filtered_labels = [row_labels[row_idx] for row_idx in eligible_indices]
    filtered_matrices = [
        [[_require_matchup_value(value) for value in matrix[row_idx]] for row_idx in eligible_indices]
        for matrix in matrices
    ]
    return filtered_labels, filtered_matrices


def _active_overall_ranking_species(ranking_profile: RankingProfile | None) -> set[str] | None:
    if ranking_profile is None:
        return None

    overall_rankings = ranking_profile.scores_by_category.get(RankingCategory.OVERALL, {})
    return {
        normalized_species
        for key, row in overall_rankings.items()
        for normalized_species in (parse_species(row.species), parse_species(key))
        if normalized_species
    }


def _ranking_filter_reason(overall_ranking_species: set[str] | None) -> str:
    if overall_ranking_species is None:
        return ""
    return " or without active overall rankings"


def _row_has_complete_matchups(row_idx: int, matrices: list[list[list[MatchupValue]]]) -> bool:
    for matrix in matrices:
        if row_idx >= len(matrix):
            return False
        if any(value is None for value in matrix[row_idx]):
            return False
    return True


def _require_matchup_value(value: MatchupValue) -> int:
    if value is None:
        raise ValueError("Missing matchup data was not filtered before optimization")
    return value


def _build_recommended_lineups(
    *,
    row_labels: list[str],
    matrices: list[list[list[int]]],
    team_indices: tuple[int, ...],
    species_cache: dict[str, tuple[str, ...]],
    ranking_profile: RankingProfile | None = None,
    species_by_row: list[str] | None = None,
    pokemon_types_by_row: list[tuple[str, ...]] | None = None,
    type_effectiveness: dict[str, dict[str, float]] | None = None,
    threat_weights: list[float] | None = None,
    battle_frontier_points_by_row: list[int] | None = None,
    limit: int = MAX_RECOMMENDED_LINEUPS,
) -> list[dict[str, Any]]:
    if len(team_indices) < 3 or len(matrices) < 3:
        return []

    scored_lineups = []
    for lineup in enumerate_ordered_lineups(team_indices):
        score = score_ordered_lineup(
            lineup,
            matrices,
            species_by_row=species_by_row,
            ranking_profile=ranking_profile,
            pokemon_types_by_row=pokemon_types_by_row,
            type_effectiveness=type_effectiveness,
            threat_weights=threat_weights,
        )
        lineup_score = score.lineup_score if score.lineup_score is not None else score.resource_mean_score
        if score.resource_mean_score >= LINEUP_VIABILITY_THRESHOLD and lineup_score >= LINEUP_VIABILITY_THRESHOLD:
            scored_lineups.append((lineup_score, score))

    scored_lineups.sort(
        key=lambda item: (
            -item[0],
            item[1].lineup.lead_index,
            item[1].lineup.back_indices[0],
            item[1].lineup.back_indices[1],
        )
    )

    return [
        _to_recommended_lineup(
            row_labels,
            species_cache,
            lineup_score,
            score,
            battle_frontier_points_by_row,
            type_effectiveness,
        )
        for lineup_score, score in scored_lineups[:limit]
    ]


def _normalized_category_scores_by_row(
    row_species: list[str],
    ranking_profile: RankingProfile | None,
    category: RankingCategory,
) -> list[float]:
    if ranking_profile is None:
        return [0.5] * len(row_species)
    rows = ranking_profile.scores_by_category.get(category, {})
    scores = []
    for species in row_species:
        row = rows.get(species)
        scores.append(row.normalized_score if row is not None and row.normalized_score is not None else 0.5)
    return scores


def _to_recommended_lineup(
    row_labels: list[str],
    species_cache: dict[str, tuple[str, ...]],
    lineup_score: float,
    score: Any,
    battle_frontier_points_by_row: list[int] | None = None,
    type_effectiveness: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    dominating_matchups = sum(path.dominate_count for path in score.path_scores)
    overwhelming_matchups = sum(path.overwhelming_count for path in score.path_scores)
    lead = _to_team_member(score.lineup.lead_index, row_labels, species_cache)
    back_pair = [
        _to_team_member(index, row_labels, species_cache)
        for index in score.lineup.back_indices
    ]
    result: dict[str, Any] = {
        "lead": lead,
        "back_pair": back_pair,
        "team_shape": classify_lineup_shape(
            lead["types"],
            back_pair[0]["types"],
            back_pair[1]["types"],
        ),
        "lineup_score": lineup_score,
        "score_summary": {
            "mean_score": score.resource_mean_score,
            "dominating_matchups": dominating_matchups,
            "overwhelming_matchups": overwhelming_matchups,
        },
        "resource_paths": [
            {
                "name": path_score.path_name,
                "lead_shield": path.lead_shield,
                "back_shield": path.back_shield,
                "mean_best_score": path_score.mean_best_score,
                "dominating_matchups": path_score.dominate_count,
                "overwhelming_matchups": path_score.overwhelming_count,
            }
            for path, path_score in zip(LINEUP_RESOURCE_PATHS, score.path_scores, strict=True)
        ],
    }
    if score.role_fit_score is not None:
        result["score_summary"].update(
            {
                "resource_mean_score": score.resource_mean_score,
                "role_fit_score": score.role_fit_score,
            }
        )
    if score.synergy_score is not None:
        result["score_summary"].update(
            {
                "resource_mean_score": score.resource_mean_score,
                "synergy_score": score.synergy_score,
            }
        )
    result["score_breakdown"] = _lineup_score_breakdown_payload(score, lineup_score)
    result["ranking_diagnostics"] = {
        "role_assumptions": _lineup_role_assumptions(score),
        "shared_weaknesses": _shared_weaknesses(
            labels=[lead["label"], back_pair[0]["label"], back_pair[1]["label"]],
            member_types=[lead["types"], back_pair[0]["types"], back_pair[1]["types"]],
            type_effectiveness=type_effectiveness,
        ),
    }
    if battle_frontier_points_by_row is not None:
        result["battle_frontier_points_used"] = sum(
            battle_frontier_points_by_row[index]
            for index in (score.lineup.lead_index, *score.lineup.back_indices)
        )
    return result


def _roster_score_breakdown_payload(score: RosterScore) -> dict[str, Any]:
    return {
        "final_score": score.final_score,
        "components": [_weighted_component_payload(component) for component in score.components],
    }


def _weighted_component_payload(component: WeightedScoreComponent) -> dict[str, Any]:
    return {
        "name": component.name,
        "raw_value": component.raw_value,
        "weight": component.weight,
        "weighted_score": component.weighted_score,
        "diagnostics": [
            {"key": key, "value": value}
            for key, value in component.diagnostics
        ],
    }


def _lineup_score_breakdown_payload(score: Any, final_score: float) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    if score.synergy_score is not None:
        resource_weight = (
            LINEUP_RESOURCE_WITH_SYNERGY_SCORE_WEIGHT
            if score.role_fit_score is not None
            else LINEUP_RESOURCE_WITHOUT_ROLE_SYNERGY_SCORE_WEIGHT
        )
    elif score.role_fit_score is not None:
        resource_weight = LINEUP_RESOURCE_SCORE_WEIGHT
    else:
        resource_weight = 1.0

    components.append(
        _lineup_component_payload("resource_path", score.resource_mean_score, resource_weight)
    )
    if score.role_fit_score is not None:
        components.append(
            _lineup_component_payload(
                "role_fit",
                score.role_fit_score * 1000.0,
                LINEUP_ROLE_FIT_SCORE_WEIGHT,
            )
        )
    if score.synergy_score is not None:
        components.append(
            _lineup_component_payload(
                "synergy",
                score.synergy_score * 1000.0,
                LINEUP_SYNERGY_SCORE_WEIGHT,
            )
        )
    return {"final_score": final_score, "components": components}


def _lineup_component_payload(name: str, raw_value: float, weight: float) -> dict[str, Any]:
    return {
        "name": name,
        "raw_value": raw_value,
        "weight": weight,
        "weighted_score": raw_value * weight,
    }


def _lineup_role_assumptions(score: Any) -> list[str]:
    if score.role_fit_score is None:
        return []
    return [
        "Lead uses PvPoke leads ranking; backs use unordered switch/closer support rankings."
    ]


def _build_ranking_diagnostics(
    *,
    row_labels: list[str],
    col_labels: list[str],
    matrices: list[list[list[int]]],
    metrics: dict[str, Any],
    team_indices: tuple[int, ...],
    pokemon_types_by_row: list[tuple[str, ...]],
    type_effectiveness: dict[str, dict[str, float]],
    ranking_profile: RankingProfile | None,
) -> dict[str, Any]:
    key_covered_threats: list[str] = []
    no_answer_threats: list[str] = []
    single_answer_threats: list[str] = []
    for col_idx, label in enumerate(col_labels):
        answer_count = _threat_answer_count(team_indices, matrices, col_idx)
        if answer_count == 0:
            no_answer_threats.append(label)
        elif answer_count == 1:
            single_answer_threats.append(label)
        else:
            key_covered_threats.append(label)

    remaining_threats = list(dict.fromkeys(no_answer_threats + single_answer_threats))
    member_labels = [row_labels[index] for index in team_indices]
    member_types = [pokemon_types_by_row[index] for index in team_indices]

    return {
        "key_covered_threats": key_covered_threats[:5],
        "remaining_threats": remaining_threats,
        "no_answer_threats": no_answer_threats,
        "single_answer_threats": single_answer_threats,
        "shared_weaknesses": _shared_weaknesses(
            labels=member_labels,
            member_types=member_types,
            type_effectiveness=type_effectiveness,
        ),
        "role_assumptions": _role_assumptions(ranking_profile),
        "lineup_dependency": _lineup_dependency(metrics),
    }


def _threat_answer_count(
    team_indices: tuple[int, ...],
    matrices: list[list[list[int]]],
    col_idx: int,
) -> int:
    return sum(
        max(matrix[row_idx][col_idx] for matrix in matrices) > 500
        for row_idx in team_indices
    )


def _role_assumptions(ranking_profile: RankingProfile | None) -> list[str]:
    assumptions = [
        "Leads use PvPoke leads rankings when available.",
        "Back pairs use unordered PvPoke switches, closers, attackers, chargers, and consistency blends when available.",
    ]
    if ranking_profile is None:
        return assumptions
    return assumptions


def _lineup_dependency(metrics: dict[str, Any]) -> dict[str, Any]:
    best_score = float(metrics.get("lineup_best_score", 0.0))
    top_mean = float(metrics.get("lineup_top_n_mean_score", 0.0))
    viable_count = int(metrics.get("lineup_viable_count", 0))
    dependent = viable_count <= 1 or (best_score - top_mean) >= 100.0
    if viable_count <= 1:
        reason = "Only one viable ordered lineup is available."
    elif dependent:
        reason = "Best lineup is much stronger than the recommended alternatives."
    else:
        reason = "Recommended roster has multiple viable ordered lineups."
    return {
        "dependent": dependent,
        "reason": reason,
        "best_lineup_score": best_score,
        "top_lineup_mean_score": top_mean,
        "viable_lineup_count": viable_count,
    }


def _shared_weaknesses(
    *,
    labels: list[str],
    member_types: list[tuple[str, ...]] | list[list[str]],
    type_effectiveness: dict[str, dict[str, float]] | None,
) -> list[dict[str, Any]]:
    if not type_effectiveness:
        return []
    shared = []
    for attack_type in sorted(type_effectiveness):
        weak_members = [
            label
            for label, types in zip(labels, member_types, strict=True)
            if _defensive_multiplier(attack_type, tuple(types), type_effectiveness) > 1.0
        ]
        if len(weak_members) >= 2:
            shared.append({"type": attack_type, "members": weak_members})
    return shared


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


def _build_bench_utility(
    *,
    row_labels: list[str],
    matrices: list[list[list[int]]],
    team_indices: tuple[int, ...],
    species_cache: dict[str, tuple[str, ...]],
    battle_frontier_points_by_row: list[int] | None = None,
    pokemon_types_by_row: list[tuple[str, ...]] | None = None,
    type_effectiveness: dict[str, dict[str, float]] | None = None,
    threat_weights: list[float] | None = None,
) -> list[dict[str, Any]]:
    return [
        {
            "member": _to_team_member(usage.member_index, row_labels, species_cache),
            "lineups_used": usage.lineups_used,
            "lead_lineups_used": usage.lead_lineups_used,
            "back_lineups_used": usage.back_lineups_used,
            "viable_lineup_rate": usage.viable_lineup_rate,
            "all_lineup_rate": usage.all_lineup_rate,
            "best_lineup_score": usage.best_lineup_score,
            "tier": usage.tier,
            "warnings": [
                {
                    "category": warning.category,
                    "code": warning.code,
                    "severity": warning.severity,
                    "message": warning.message,
                }
                for warning in usage.warnings
            ],
        }
        for usage in score_roster_bench_utility(
            team_indices,
            matrices,
            battle_frontier_points_by_row=battle_frontier_points_by_row,
            pokemon_types_by_row=pokemon_types_by_row,
            type_effectiveness=type_effectiveness,
            threat_weights=threat_weights,
        )
    ]


def _build_actionable_bench_utility(
    *,
    row_labels: list[str],
    matrices: list[list[list[int]]],
    team_indices: tuple[int, ...],
    species_cache: dict[str, tuple[str, ...]],
    battle_frontier_points_by_row: list[int] | None = None,
    pokemon_types_by_row: list[tuple[str, ...]] | None = None,
    type_effectiveness: dict[str, dict[str, float]] | None = None,
    threat_weights: list[float] | None = None,
) -> list[dict[str, Any]]:
    if battle_frontier_points_by_row is None:
        return []

    return [
        entry
        for entry in _build_bench_utility(
            row_labels=row_labels,
            matrices=matrices,
            team_indices=team_indices,
            species_cache=species_cache,
            battle_frontier_points_by_row=battle_frontier_points_by_row,
            pokemon_types_by_row=pokemon_types_by_row,
            type_effectiveness=type_effectiveness,
            threat_weights=threat_weights,
        )
        if any(warning["category"] == "battle_frontier" for warning in entry["warnings"])
    ]


def _to_team_member(
    row_idx: int,
    row_labels: list[str],
    species_cache: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    return to_team_members((row_idx,), row_labels, species_cache)[0]
