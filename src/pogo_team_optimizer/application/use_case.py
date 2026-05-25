from __future__ import annotations

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
    LINEUP_VIABILITY_THRESHOLD,
    classify_lineup_shape,
    enumerate_ordered_lineups,
    score_battle_frontier_lineup_usage,
    score_roster_bench_utility,
    score_ordered_lineup,
)
from pogo_team_optimizer.application.normalization import parse_species
from pogo_team_optimizer.application.optimizer import TeamOptimizer
from pogo_team_optimizer.domain.interfaces import (
    BattleFrontierPointsRepository,
    PokemonRepository,
    SimulationMatrixRepository,
    SwitchRankingsRepository,
)


MAX_RECOMMENDED_LINEUPS = 5


class AnalyzeMetaUseCase:
    def __init__(
        self,
        simulation_repository: SimulationMatrixRepository,
        pokemon_repository: PokemonRepository,
        switch_rankings_repository: SwitchRankingsRepository | None = None,
        battle_frontier_points_repository: BattleFrontierPointsRepository | None = None,
    ) -> None:
        self.simulation_repository = simulation_repository
        self.pokemon_repository = pokemon_repository
        self.switch_rankings_repository = switch_rankings_repository
        self.battle_frontier_points_repository = battle_frontier_points_repository

    def execute(
        self,
        top_threats: int = 10,
        top_lineups: int = MAX_RECOMMENDED_LINEUPS,
        seed: int = 7,
        restarts: int = 250,
        safety_priority: str = "medium",
    ) -> dict[str, Any]:
        row_labels, col_labels, matrices = self.simulation_repository.load()
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

        bulk_by_row: list[float] = []
        safety_by_row: list[float] = []
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
            battle_frontier_points_by_row = [
                self.battle_frontier_points_repository.get_points(parse_species(label))
                for label in row_labels
            ]

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
            battle_frontier_points_by_row=battle_frontier_points_by_row,
            seed=seed,
        )
        best_team = optimizer.optimize(
            restarts=restarts,
            safety_floor=safety_floor,
            min_safe_members=min_safe_members,
            safe_member_floor=safe_member_floor,
        )

        species_cache = {
            parse_species(label): self.pokemon_repository.get_types(parse_species(label))
            for label in row_labels
        }

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

        result = {
            "recommended_team": {
                "members": to_team_members(best_team.member_indices, row_labels, species_cache),
                "score": best_team.score,
                "bulk_score": sum(bulk_by_row[idx] for idx in best_team.member_indices)
                / len(best_team.member_indices),
                "safety_score": sum(safety_by_row[idx] for idx in best_team.member_indices)
                / len(best_team.member_indices),
                "metrics": metrics,
                "bench_utility": _build_bench_utility(
                    row_labels=row_labels,
                    matrices=matrices,
                    team_indices=best_team.member_indices,
                    species_cache=species_cache,
                    battle_frontier_points_by_row=battle_frontier_points_by_row,
                ),
                "shadow_count": sum(
                    1 for idx in best_team.member_indices if "(Shadow)" in row_labels[idx]
                ),
            },
            "coverage": coverage_by_shield(matrices, best_team.member_indices, weights),
            "threats": build_threats(
                row_labels,
                col_labels,
                matrices,
                best_team.member_indices,
                top_n=top_threats,
            ),
            "safe_cores": [],
            "target_map": build_target_map(
                row_labels, col_labels, matrices, best_team.member_indices
            ),
            "recommended_lineups": _build_recommended_lineups(
                row_labels=row_labels,
                matrices=matrices,
                team_indices=best_team.member_indices,
                species_cache=species_cache,
                battle_frontier_points_by_row=battle_frontier_points_by_row,
                limit=top_lineups,
            ),
        }
        return result


def _build_recommended_lineups(
    *,
    row_labels: list[str],
    matrices: list[list[list[int]]],
    team_indices: tuple[int, ...],
    species_cache: dict[str, tuple[str, ...]],
    battle_frontier_points_by_row: list[int] | None = None,
    limit: int = MAX_RECOMMENDED_LINEUPS,
) -> list[dict[str, Any]]:
    if len(team_indices) < 3 or len(matrices) < 3:
        return []

    scored_lineups = []
    for lineup in enumerate_ordered_lineups(team_indices):
        score = score_ordered_lineup(lineup, matrices)
        lineup_score = sum(path.mean_best_score for path in score.path_scores) / len(
            score.path_scores
        )
        if lineup_score >= LINEUP_VIABILITY_THRESHOLD:
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
        )
        for lineup_score, score in scored_lineups[:limit]
    ]


def _to_recommended_lineup(
    row_labels: list[str],
    species_cache: dict[str, tuple[str, ...]],
    lineup_score: float,
    score: Any,
    battle_frontier_points_by_row: list[int] | None = None,
) -> dict[str, Any]:
    dominating_matchups = sum(path.dominate_count for path in score.path_scores)
    overwhelming_matchups = sum(path.overwhelming_count for path in score.path_scores)
    lead = _to_team_member(score.lineup.lead_index, row_labels, species_cache)
    back_pair = [
        _to_team_member(index, row_labels, species_cache)
        for index in score.lineup.back_indices
    ]
    result = {
        "lead": lead,
        "back_pair": back_pair,
        "team_shape": classify_lineup_shape(
            lead["types"],
            back_pair[0]["types"],
            back_pair[1]["types"],
        ),
        "lineup_score": lineup_score,
        "score_summary": {
            "mean_score": lineup_score,
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
    if battle_frontier_points_by_row is not None:
        result["battle_frontier_points_used"] = sum(
            battle_frontier_points_by_row[index]
            for index in (score.lineup.lead_index, *score.lineup.back_indices)
        )
    return result


def _build_bench_utility(
    *,
    row_labels: list[str],
    matrices: list[list[list[int]]],
    team_indices: tuple[int, ...],
    species_cache: dict[str, tuple[str, ...]],
    battle_frontier_points_by_row: list[int] | None = None,
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
        )
    ]


def _to_team_member(
    row_idx: int,
    row_labels: list[str],
    species_cache: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    return to_team_members((row_idx,), row_labels, species_cache)[0]
