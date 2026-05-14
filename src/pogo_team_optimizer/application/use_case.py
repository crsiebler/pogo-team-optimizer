from __future__ import annotations

from collections import defaultdict
from typing import Any

from pogo_team_optimizer.application.analyzers import (
    build_core_role_recommendation,
    build_target_map,
    build_threats,
    coverage_by_shield,
    to_team_members,
)
from pogo_team_optimizer.application.normalization import parse_species
from pogo_team_optimizer.application.optimizer import TeamOptimizer
from pogo_team_optimizer.domain.interfaces import (
    BattleFrontierPointsRepository,
    PokemonRepository,
    SimulationMatrixRepository,
    SwitchRankingsRepository,
)


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
        top_cores: int = 5,
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

        safe_cores = optimizer.rank_safe_cores(best_team.member_indices, top_n=top_cores)

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
        }
        if battle_frontier_points_by_row is not None:
            battle_frontier_team_points = [
                battle_frontier_points_by_row[idx] for idx in best_team.member_indices
            ]
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
            "safe_cores": [
                {
                    "members": to_team_members(core.member_indices, row_labels, species_cache),
                    "score": core.score,
                    **build_core_role_recommendation(
                        row_labels=row_labels,
                        col_labels=col_labels,
                        matrices=matrices,
                        core_indices=core.member_indices,
                        safety_by_row=safety_by_row,
                    ),
                }
                for core in safe_cores
            ],
            "target_map": build_target_map(
                row_labels, col_labels, matrices, best_team.member_indices
            ),
        }
        return result
