from __future__ import annotations

from collections import defaultdict

from pogo_team_optimizer.application.analyzers import (
    build_target_map,
    build_threats,
    coverage_by_shield,
    to_team_members,
)
from pogo_team_optimizer.application.normalization import parse_species
from pogo_team_optimizer.application.optimizer import TeamOptimizer
from pogo_team_optimizer.domain.interfaces import PokemonRepository, SimulationMatrixRepository


class AnalyzeMetaUseCase:
    def __init__(
        self,
        simulation_repository: SimulationMatrixRepository,
        pokemon_repository: PokemonRepository,
    ) -> None:
        self.simulation_repository = simulation_repository
        self.pokemon_repository = pokemon_repository

    def execute(
        self,
        top_threats: int = 10,
        top_cores: int = 5,
        seed: int = 7,
        restarts: int = 250,
    ) -> dict:
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
        for label in row_labels:
            species = parse_species(label)
            stats = self.pokemon_repository.get_base_stats(species)
            if stats is None:
                bulk_by_row.append(0.0)
                continue
            atk, defense, hp = stats
            if atk <= 0:
                bulk_by_row.append(0.0)
                continue
            bulk_by_row.append((defense * hp) / atk)

        optimizer = TeamOptimizer(row_labels, col_labels, matrices, bulk_by_row=bulk_by_row, seed=seed)
        best_team = optimizer.optimize(restarts=restarts)

        safe_cores = optimizer.rank_safe_cores(best_team.member_indices, top_n=top_cores)

        species_cache = {
            parse_species(label): self.pokemon_repository.get_types(parse_species(label))
            for label in row_labels
        }

        total_pairs = len(col_labels) * len(matrices)
        score = best_team.score
        dominate_count = int(score[9])
        overwhelming_count = int(score[10])
        single_cover_pairs = int(-score[4])
        no_cover_pairs = int(-score[11])
        metrics = {
            "pair_coverage": int(score[0]),
            "full_col_coverage": int(score[1]),
            "redundant_coverage_2plus": int(score[2]),
            "redundant_coverage_3plus": int(score[3]),
            "single_cover_pairs": single_cover_pairs,
            "single_cover_rate": single_cover_pairs / total_pairs,
            "no_cover_pairs": no_cover_pairs,
            "no_cover_rate": no_cover_pairs / total_pairs,
            "bulk_score": float(score[5]),
            "consistency_score": float(score[6]),
            "weighted_worst_best_score": float(score[7]),
            "mean_best_score": float(score[8]),
            "dominate_count": dominate_count,
            "dominate_rate": dominate_count / total_pairs,
            "overwhelming_count": overwhelming_count,
            "overwhelming_rate": overwhelming_count / total_pairs,
            "total_pairs": total_pairs,
            "bulk_pool_min": min(bulk_by_row) if bulk_by_row else 0.0,
            "bulk_pool_max": max(bulk_by_row) if bulk_by_row else 0.0,
            "bulk_pool_mean": (sum(bulk_by_row) / len(bulk_by_row)) if bulk_by_row else 0.0,
        }

        result = {
            "recommended_team": {
                "members": to_team_members(best_team.member_indices, row_labels, species_cache),
                "score": best_team.score,
                "bulk_score": sum(bulk_by_row[idx] for idx in best_team.member_indices)
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
                }
                for core in safe_cores
            ],
            "target_map": build_target_map(row_labels, col_labels, matrices, best_team.member_indices),
        }
        return result
