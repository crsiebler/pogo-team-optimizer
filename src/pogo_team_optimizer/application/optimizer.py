from __future__ import annotations

import itertools
import logging
import random
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from pogo_team_optimizer.application.lineups import (
    LINEUP_VIABILITY_THRESHOLD,
    ROSTER_LINEUP_TOP_N,
    OrderedLineup,
    RosterLineupScore,
    enumerate_ordered_lineups,
    score_ordered_lineup,
)
from pogo_team_optimizer.application.normalization import parse_base_species, parse_species

LOGGER = logging.getLogger(__name__)
OPTIMIZER_PROGRESS_EVALUATIONS = 10000
MAX_OPTIMIZER_WORKERS = 32


@dataclass(frozen=True)
class TeamSolution:
    member_indices: tuple[int, ...]
    score: tuple[float, ...]


@dataclass(frozen=True)
class OptimizerRestartBatch:
    worker_index: int
    restarts: int
    seed: int
    team_size: int
    safety_floor: float | None
    min_safe_members: int
    safe_member_floor: float
    row_labels: list[str]
    col_labels: list[str]
    matrices: list[list[list[int]]]
    bulk_by_row: list[float]
    safety_by_row: list[float]
    pokemon_types_by_row: list[tuple[str, ...]]
    move_types_by_row: list[tuple[str, ...]]
    type_effectiveness: dict[str, dict[str, float]]
    battle_frontier_points_by_row: list[int] | None
    battle_frontier_max_points: int
    battle_frontier_max_five_point_members: int
    battle_frontier_max_mega_members: int


class TeamOptimizer:
    def __init__(
        self,
        row_labels: list[str],
        col_labels: list[str],
        matrices: list[list[list[int]]],
        bulk_by_row: list[float],
        safety_by_row: list[float] | None = None,
        pokemon_types_by_row: list[tuple[str, ...]] | None = None,
        move_types_by_row: list[tuple[str, ...]] | None = None,
        type_effectiveness: dict[str, dict[str, float]] | None = None,
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
        # Meta-relative viability guard: below-average roster bulk is penalized before lineup quality.
        self.bulk_floor = sum(bulk_by_row) / len(bulk_by_row) if bulk_by_row else 0.0
        if safety_by_row is None:
            self.safety_by_row = [60.0] * len(row_labels)
        elif len(safety_by_row) != len(row_labels):
            raise ValueError("safety_by_row length must match row labels")
        else:
            self.safety_by_row = safety_by_row
        if pokemon_types_by_row is None:
            self.pokemon_types_by_row: list[tuple[str, ...]] = [tuple() for _ in row_labels]
        elif len(pokemon_types_by_row) != len(row_labels):
            raise ValueError("pokemon_types_by_row length must match row labels")
        else:
            self.pokemon_types_by_row = pokemon_types_by_row
        if move_types_by_row is None:
            self.move_types_by_row: list[tuple[str, ...]] = [tuple() for _ in row_labels]
        elif len(move_types_by_row) != len(row_labels):
            raise ValueError("move_types_by_row length must match row labels")
        else:
            self.move_types_by_row = move_types_by_row
        self.type_effectiveness = type_effectiveness or {}
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
        self.seed = seed
        self.random = random.Random(seed)
        self._team_score_cache: dict[tuple[int, ...], tuple[float, ...]] = {}
        self._lineup_mean_score_cache: dict[OrderedLineup, float] = {}

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
        workers: int = 1,
    ) -> TeamSolution:
        if workers < 1:
            raise ValueError("workers must be at least 1")
        if workers > MAX_OPTIMIZER_WORKERS:
            raise ValueError(f"workers must be at most {MAX_OPTIMIZER_WORKERS}")
        if workers == 1 or restarts <= 1:
            return self._optimize_single_process(
                team_size=team_size,
                restarts=restarts,
                safety_floor=safety_floor,
                min_safe_members=min_safe_members,
                safe_member_floor=safe_member_floor,
            )

        return self._optimize_parallel_processes(
            team_size=team_size,
            restarts=restarts,
            safety_floor=safety_floor,
            min_safe_members=min_safe_members,
            safe_member_floor=safe_member_floor,
            workers=workers,
        )

    def _optimize_single_process(
        self,
        team_size: int,
        restarts: int,
        safety_floor: float | None,
        min_safe_members: int,
        safe_member_floor: float,
    ) -> TeamSolution:
        LOGGER.info(
            "optimizer start rows=%s cols=%s shields=%s restarts=%s team_size=%s",
            len(self.row_labels),
            len(self.col_labels),
            len(self.matrices),
            restarts,
            team_size,
        )
        best: TeamSolution | None = None
        evaluated_candidates = 0
        progress_interval = max(1, restarts // 10)
        for restart_index in range(restarts):
            if restart_index == 0 or (restart_index + 1) % progress_interval == 0:
                LOGGER.info("optimizer restart %s/%s", restart_index + 1, restarts)
            candidate = self._random_team(team_size)
            score = self._score_team(candidate)
            evaluated_candidates += 1
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
                            evaluated_candidates += 1
                            if evaluated_candidates % OPTIMIZER_PROGRESS_EVALUATIONS == 0:
                                LOGGER.info(
                                    "optimizer evaluated=%s restart=%s/%s candidate=%s",
                                    evaluated_candidates,
                                    restart_index + 1,
                                    restarts,
                                    ",".join(str(idx) for idx in candidate),
                                )
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
                                LOGGER.info(
                                    "optimizer accepted swap restart=%s/%s score=%.2f team=%s",
                                    restart_index + 1,
                                    restarts,
                                    score[13],
                                    ",".join(str(idx) for idx in candidate),
                                )
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
                LOGGER.info(
                    "optimizer new best restart=%s/%s score=%.2f team=%s",
                    restart_index + 1,
                    restarts,
                    best.score[13],
                    ",".join(str(idx) for idx in best.member_indices),
                )
        if best is None:
            raise RuntimeError("Failed to optimize team")
        LOGGER.info(
            "optimizer complete evaluated=%s best_score=%.2f team=%s",
            evaluated_candidates,
            best.score[13],
            ",".join(str(idx) for idx in best.member_indices),
        )
        return best

    def _optimize_parallel_processes(
        self,
        team_size: int,
        restarts: int,
        safety_floor: float | None,
        min_safe_members: int,
        safe_member_floor: float,
        workers: int,
    ) -> TeamSolution:
        active_workers = min(workers, restarts)
        batch_sizes = _split_restart_batches(restarts, active_workers)
        batches = [
            OptimizerRestartBatch(
                worker_index=worker_index,
                restarts=batch_restarts,
                seed=self.seed + (worker_index * 1_000_003),
                team_size=team_size,
                safety_floor=safety_floor,
                min_safe_members=min_safe_members,
                safe_member_floor=safe_member_floor,
                row_labels=self.row_labels,
                col_labels=self.col_labels,
                matrices=self.matrices,
                bulk_by_row=self.bulk_by_row,
                safety_by_row=self.safety_by_row,
                pokemon_types_by_row=self.pokemon_types_by_row,
                move_types_by_row=self.move_types_by_row,
                type_effectiveness=self.type_effectiveness,
                battle_frontier_points_by_row=(
                    self.battle_frontier_points_by_row if self.has_battle_frontier_rules else None
                ),
                battle_frontier_max_points=self.battle_frontier_max_points,
                battle_frontier_max_five_point_members=(
                    self.battle_frontier_max_five_point_members
                ),
                battle_frontier_max_mega_members=self.battle_frontier_max_mega_members,
            )
            for worker_index, batch_restarts in enumerate(batch_sizes)
        ]

        LOGGER.info(
            "optimizer process batches workers=%s restarts=%s chunks=%s",
            active_workers,
            restarts,
            ",".join(str(size) for size in batch_sizes),
        )
        with ProcessPoolExecutor(max_workers=active_workers) as executor:
            results = list(executor.map(_optimize_restart_batch, batches))

        best: TeamSolution | None = None
        for _, candidate in sorted(results, key=lambda item: item[0]):
            if best is None:
                best = candidate
                continue
            candidate_key = self._comparison_key(
                list(candidate.member_indices),
                candidate.score,
                safety_floor=safety_floor,
                min_safe_members=min_safe_members,
                safe_member_floor=safe_member_floor,
            )
            best_key = self._comparison_key(
                list(best.member_indices),
                best.score,
                safety_floor=safety_floor,
                min_safe_members=min_safe_members,
                safe_member_floor=safe_member_floor,
            )
            if candidate_key > best_key:
                best = candidate
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
        cache_key = tuple(sorted(team_indices))
        cached = self._team_score_cache.get(cache_key)
        if cached is not None:
            return cached

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
        lineup_score = self._score_team_lineups(team_indices)
        defensive_type_score = self._score_defensive_type_profile(team_indices)
        offensive_move_score = self._score_offensive_move_profile(team_indices)

        score = (
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
            lineup_score.objective_score,
            lineup_score.best_lineup_score,
            lineup_score.top_lineup_mean,
            float(lineup_score.viable_lineup_count),
            defensive_type_score,
            offensive_move_score,
        )
        self._team_score_cache[cache_key] = score
        return score

    def _score_team_lineups(self, team_indices: list[int]) -> RosterLineupScore:
        if len(team_indices) < 3 or len(self.matrices) < 3:
            return RosterLineupScore(0.0, 0.0, 0.0, 0)

        lineup_scores = sorted(
            (self._lineup_mean_score(lineup) for lineup in enumerate_ordered_lineups(team_indices)),
            reverse=True,
        )
        if not lineup_scores:
            return RosterLineupScore(0.0, 0.0, 0.0, 0)

        top_scores = lineup_scores[:ROSTER_LINEUP_TOP_N]
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

    def _lineup_mean_score(self, lineup: OrderedLineup) -> float:
        cached = self._lineup_mean_score_cache.get(lineup)
        if cached is not None:
            return cached

        score = score_ordered_lineup(lineup, self.matrices)
        mean_score = sum(path.mean_best_score for path in score.path_scores) / len(score.path_scores)
        self._lineup_mean_score_cache[lineup] = mean_score
        return mean_score

    def _score_defensive_type_profile(self, team_indices: list[int]) -> float:
        if not self.type_effectiveness:
            return 0.0

        shared_weakness_penalty = 0.0
        resistance_score = 0.0
        for attack_type in self.type_effectiveness:
            weakness_count = 0
            resistance_count = 0
            for row_idx in team_indices:
                multiplier = self._defensive_multiplier(attack_type, self.pokemon_types_by_row[row_idx])
                if multiplier > 1.0:
                    weakness_count += 1
                elif multiplier < 1.0:
                    resistance_count += 1
            shared_weakness_penalty += float(weakness_count * weakness_count)
            resistance_score += float(resistance_count)

        return resistance_score - shared_weakness_penalty

    def _score_offensive_move_profile(self, team_indices: list[int]) -> float:
        if not self.type_effectiveness:
            return 0.0

        move_types = {
            move_type
            for row_idx in team_indices
            for move_type in self.move_types_by_row[row_idx]
            if move_type in self.type_effectiveness
        }
        if not move_types:
            return 0.0

        defender_types = {
            defender_type
            for effectiveness_by_defender in self.type_effectiveness.values()
            for defender_type in effectiveness_by_defender
        }
        score = 0.0
        for defender_type in defender_types:
            best_multiplier = max(
                self.type_effectiveness[move_type].get(defender_type, 1.0)
                for move_type in move_types
            )
            if best_multiplier > 1.0:
                score += 1.0
            score += best_multiplier - 1.0
        return score

    def _defensive_multiplier(self, attack_type: str, defender_types: tuple[str, ...]) -> float:
        multiplier = 1.0
        effectiveness_by_defender = self.type_effectiveness.get(attack_type, {})
        for defender_type in defender_types:
            multiplier *= effectiveness_by_defender.get(defender_type, 1.0)
        return multiplier

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
        team_bulk_score = score[5]
        floor_deficit = 0.0
        if safety_floor is not None and team_safety_score < safety_floor:
            floor_deficit = safety_floor - team_safety_score

        bulk_deficit = max(0.0, self.bulk_floor - team_bulk_score)
        safe_member_count = sum(
            1 for row_idx in team_indices if self.safety_by_row[row_idx] >= safe_member_floor
        )
        safe_member_deficit = float(max(0, min_safe_members - safe_member_count))

        return (
            -floor_deficit,
            -safe_member_deficit,
            -bulk_deficit,
            score[13],
            score[15],
            score[16],
            score[14],
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


def _split_restart_batches(restarts: int, workers: int) -> list[int]:
    base_restarts, extra_restarts = divmod(restarts, workers)
    return [
        base_restarts + (1 if worker_index < extra_restarts else 0)
        for worker_index in range(workers)
    ]


def _optimize_restart_batch(batch: OptimizerRestartBatch) -> tuple[int, TeamSolution]:
    optimizer = TeamOptimizer(
        row_labels=batch.row_labels,
        col_labels=batch.col_labels,
        matrices=batch.matrices,
        bulk_by_row=batch.bulk_by_row,
        safety_by_row=batch.safety_by_row,
        pokemon_types_by_row=batch.pokemon_types_by_row,
        move_types_by_row=batch.move_types_by_row,
        type_effectiveness=batch.type_effectiveness,
        battle_frontier_points_by_row=batch.battle_frontier_points_by_row,
        battle_frontier_max_points=batch.battle_frontier_max_points,
        battle_frontier_max_five_point_members=batch.battle_frontier_max_five_point_members,
        battle_frontier_max_mega_members=batch.battle_frontier_max_mega_members,
        seed=batch.seed,
    )
    return (
        batch.worker_index,
        optimizer._optimize_single_process(
            team_size=batch.team_size,
            restarts=batch.restarts,
            safety_floor=batch.safety_floor,
            min_safe_members=batch.min_safe_members,
            safe_member_floor=batch.safe_member_floor,
        ),
    )
