from __future__ import annotations

import itertools
import random
from collections import defaultdict
from dataclasses import dataclass

from pogo_team_optimizer.application.normalization import parse_base_species, parse_species


@dataclass(frozen=True)
class TeamSolution:
    member_indices: tuple[int, ...]
    score: tuple[float, ...]


class TeamOptimizer:
    def __init__(
        self,
        row_labels: list[str],
        col_labels: list[str],
        matrices: list[list[list[int]]],
        bulk_by_row: list[float],
        safety_by_row: list[float] | None = None,
        battle_frontier_points_by_row: list[int] | None = None,
        battle_frontier_max_points: int = 11,
        battle_frontier_max_five_point_members: int = 1,
        battle_frontier_max_mega_members: int = 1,
        seed: int = 7,
    ) -> None:
        self.row_labels = row_labels
        self.col_labels = col_labels
        self.matrices = matrices
        self.bulk_by_row = bulk_by_row
        if safety_by_row is None:
            self.safety_by_row = [60.0] * len(row_labels)
        elif len(safety_by_row) != len(row_labels):
            raise ValueError("safety_by_row length must match row labels")
        else:
            self.safety_by_row = safety_by_row
        if battle_frontier_points_by_row is None:
            self.battle_frontier_points_by_row = [0] * len(row_labels)
            self.has_battle_frontier_rules = False
        elif len(battle_frontier_points_by_row) != len(row_labels):
            raise ValueError("battle_frontier_points_by_row length must match row labels")
        else:
            self.battle_frontier_points_by_row = battle_frontier_points_by_row
            self.has_battle_frontier_rules = True
        self.battle_frontier_max_points = battle_frontier_max_points
        self.battle_frontier_max_five_point_members = battle_frontier_max_five_point_members
        self.battle_frontier_max_mega_members = battle_frontier_max_mega_members
        self.random = random.Random(seed)

        self.row_species = [parse_species(label) for label in row_labels]
        self.row_base_species = [parse_base_species(s) for s in self.row_species]
        self.row_is_mega = ["(Mega" in species for species in self.row_species]
        self.col_species = [parse_species(label) for label in col_labels]

        self.base_to_rows: dict[str, list[int]] = defaultdict(list)
        for index, base in enumerate(self.row_base_species):
            self.base_to_rows[base].append(index)

        species_groups: dict[str, list[int]] = defaultdict(list)
        for col_idx, species in enumerate(self.col_species):
            species_groups[species].append(col_idx)
        self.weights = [0.0] * len(self.col_labels)
        group_count = len(species_groups)
        for indices in species_groups.values():
            weight = 1.0 / group_count / len(indices)
            for col_idx in indices:
                self.weights[col_idx] = weight

    def optimize(
        self,
        team_size: int = 6,
        restarts: int = 250,
        safety_floor: float | None = None,
        min_safe_members: int = 0,
        safe_member_floor: float = 90.0,
    ) -> TeamSolution:
        best: TeamSolution | None = None
        for _ in range(restarts):
            candidate = self._random_team(team_size)
            score = self._score_team(candidate)
            key = self._comparison_key(
                candidate,
                score,
                safety_floor=safety_floor,
                min_safe_members=min_safe_members,
                safe_member_floor=safe_member_floor,
            )
            improved = True
            while improved:
                improved = False
                current_bases = {self.row_base_species[i] for i in candidate}
                for pos in range(team_size):
                    original = candidate[pos]
                    original_base = self.row_base_species[original]
                    for base, rows in self.base_to_rows.items():
                        if base in current_bases and base != original_base:
                            continue
                        for row_idx in rows:
                            if row_idx == original:
                                continue
                            candidate[pos] = row_idx
                            if not self._is_team_legal(candidate):
                                continue
                            next_score = self._score_team(candidate)
                            next_key = self._comparison_key(
                                candidate,
                                next_score,
                                safety_floor=safety_floor,
                                min_safe_members=min_safe_members,
                                safe_member_floor=safe_member_floor,
                            )
                            if next_key > key:
                                score = next_score
                                key = next_key
                                current_bases = {self.row_base_species[i] for i in candidate}
                                improved = True
                                break
                        if improved:
                            break
                    if improved:
                        break
                    candidate[pos] = original
            candidate_solution = TeamSolution(tuple(candidate), score)
            if best is None:
                best = candidate_solution
                continue
            best_key = self._comparison_key(
                list(best.member_indices),
                best.score,
                safety_floor=safety_floor,
                min_safe_members=min_safe_members,
                safe_member_floor=safe_member_floor,
            )
            if key > best_key:
                best = candidate_solution
        if best is None:
            raise RuntimeError("Failed to optimize team")
        return best

    def rank_safe_cores(
        self,
        team_indices: tuple[int, ...],
        top_n: int = 5,
    ) -> list[TeamSolution]:
        scored: list[TeamSolution] = []
        for combo in itertools.combinations(team_indices, 3):
            score = self._score_team(list(combo))
            scored.append(TeamSolution(combo, score))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_n]

    def _random_team(self, team_size: int) -> list[int]:
        for _ in range(1000):
            selected_bases = self.random.sample(list(self.base_to_rows.keys()), k=team_size)
            team = [self.random.choice(self.base_to_rows[base]) for base in selected_bases]
            if self._is_team_legal(team):
                return team
        raise RuntimeError("Failed to generate legal team")

    def _is_team_legal(self, team_indices: list[int]) -> bool:
        if len({self.row_base_species[idx] for idx in team_indices}) != len(team_indices):
            return False
        if not self.has_battle_frontier_rules:
            return True

        total_points = sum(self.battle_frontier_points_by_row[idx] for idx in team_indices)
        if total_points > self.battle_frontier_max_points:
            return False

        five_point_count = sum(self.battle_frontier_points_by_row[idx] == 5 for idx in team_indices)
        if five_point_count > self.battle_frontier_max_five_point_members:
            return False

        mega_count = sum(self.row_is_mega[idx] for idx in team_indices)
        if mega_count > self.battle_frontier_max_mega_members:
            return False

        return True

    def _score_team(self, team_indices: list[int]) -> tuple[float, ...]:
        pair_coverage = 0
        full_col_coverage = 0
        redundant_coverage_2plus = 0
        redundant_coverage_3plus = 0
        single_cover_pairs = 0
        no_cover_pairs = 0
        team_bulk_score = sum(self.bulk_by_row[row_idx] for row_idx in team_indices) / len(
            team_indices
        )
        team_safety_score = sum(self.safety_by_row[row_idx] for row_idx in team_indices) / len(
            team_indices
        )
        dominate_count = 0
        overwhelming_count = 0
        mean_best_score = 0.0
        weighted_worst_best_score = 0.0

        shield_count = len(self.matrices)
        col_count = len(self.col_labels)
        total_pairs = shield_count * col_count

        for col_idx in range(col_count):
            covered_in_shield: list[bool] = []
            best_scores: list[int] = []
            for shield_idx in range(shield_count):
                winners = 0
                best = -1
                for row_idx in team_indices:
                    value = self.matrices[shield_idx][row_idx][col_idx]
                    if value > best:
                        best = value
                    if value > 500:
                        winners += 1

                best_scores.append(best)
                won = best > 500
                covered_in_shield.append(won)
                if won:
                    pair_coverage += 1
                else:
                    no_cover_pairs += 1

                if winners >= 2:
                    redundant_coverage_2plus += 1
                if winners >= 3:
                    redundant_coverage_3plus += 1
                if winners == 1:
                    single_cover_pairs += 1

                if best > 650:
                    dominate_count += 1
                if best < 350:
                    overwhelming_count += 1
                mean_best_score += best
            if all(covered_in_shield):
                full_col_coverage += 1
            weighted_worst_best_score += self.weights[col_idx] * min(best_scores)
        mean_best_score /= total_pairs
        dominate_rate = dominate_count / total_pairs
        overwhelming_rate = overwhelming_count / total_pairs
        consistency_score = mean_best_score + (75.0 * dominate_rate) - (125.0 * overwhelming_rate)

        return (
            float(pair_coverage),
            float(full_col_coverage),
            float(-no_cover_pairs),
            float(-single_cover_pairs),
            weighted_worst_best_score,
            team_bulk_score,
            team_safety_score,
            consistency_score,
            float(redundant_coverage_2plus),
            float(redundant_coverage_3plus),
            mean_best_score,
            float(dominate_count),
            float(-overwhelming_count),
        )

    def _comparison_key(
        self,
        team_indices: list[int],
        score: tuple[float, ...],
        *,
        safety_floor: float | None,
        min_safe_members: int,
        safe_member_floor: float,
    ) -> tuple[float, ...]:
        team_safety_score = score[6]
        floor_deficit = 0.0
        if safety_floor is not None and team_safety_score < safety_floor:
            floor_deficit = safety_floor - team_safety_score

        safe_member_count = sum(
            1 for row_idx in team_indices if self.safety_by_row[row_idx] >= safe_member_floor
        )
        safe_member_deficit = float(max(0, min_safe_members - safe_member_count))

        return (
            -floor_deficit,
            -safe_member_deficit,
            score[2],
            score[3],
            score[4],
            score[6],
            score[5],
            score[0],
            score[1],
            score[7],
            score[8],
            score[9],
            score[10],
            score[11],
            score[12],
        )
