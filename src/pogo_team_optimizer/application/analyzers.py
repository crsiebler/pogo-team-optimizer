from __future__ import annotations

import itertools
from typing import Any

from pogo_team_optimizer.application.normalization import parse_base_species, parse_species


def coverage_by_shield(
    matrices: list[list[list[int]]],
    team_indices: tuple[int, ...],
    weights: list[float],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    col_count = len(matrices[0][0])
    for shield_idx, matrix in enumerate(matrices):
        wins = 0
        draws = 0
        losses = 0
        weighted_wins = 0.0
        for col_idx in range(col_count):
            best = max(matrix[row_idx][col_idx] for row_idx in team_indices)
            if best > 500:
                wins += 1
                weighted_wins += weights[col_idx]
            elif best == 500:
                draws += 1
            else:
                losses += 1
        summaries.append(
            {
                "shield": shield_idx,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "weighted_wins": round(weighted_wins, 6),
            }
        )
    return summaries


def build_threats(
    row_labels: list[str],
    col_labels: list[str],
    matrices: list[list[list[int]]],
    team_indices: tuple[int, ...],
    top_n: int,
    threat_indices: list[int] | None = None,
) -> list[dict[str, Any]]:
    threats: list[dict[str, Any]] = []
    fallback_threats: list[dict[str, Any]] = []
    candidate_indices = threat_indices if threat_indices is not None else list(range(len(col_labels)))
    for col_idx in candidate_indices:
        opponent_label = col_labels[col_idx]
        shield_best_scores: list[int] = []
        shield_best_members: list[str] = []
        shield_fragility: list[dict[str, Any]] = []
        no_cover_count = 0
        single_cover_count = 0

        for shield_idx, matrix in enumerate(matrices):
            best_score = -1
            best_member = ""
            winners: list[tuple[str, int]] = []
            best_loser_score = -1
            best_loser_member = ""

            for row_idx in team_indices:
                value = matrix[row_idx][col_idx]
                if value > best_score:
                    best_score = value
                    best_member = row_labels[row_idx]
                if value > 500:
                    winners.append((row_labels[row_idx], value))
                elif value > best_loser_score:
                    best_loser_score = value
                    best_loser_member = row_labels[row_idx]

            shield_best_scores.append(best_score)
            shield_best_members.append(best_member)

            winner_count = len(winners)
            if winner_count == 0:
                no_cover_count += 1
            elif winner_count == 1:
                single_cover_count += 1

            if winner_count <= 1:
                shield_fragility.append(
                    {
                        "shield": shield_idx,
                        "winner_count": winner_count,
                        "only_answer": winners[0][0] if winner_count == 1 else None,
                        "only_answer_score": winners[0][1] if winner_count == 1 else None,
                        "best_loser": best_loser_member if winner_count == 0 else None,
                        "best_loser_score": best_loser_score if winner_count == 0 else None,
                    }
                )

        base_item = {
            "opponent_label": opponent_label,
            "min_best_score": min(shield_best_scores),
            "avg_best_score": sum(shield_best_scores) / len(shield_best_scores),
            "shield_best_scores": shield_best_scores,
            "shield_best_members": shield_best_members,
            "single_cover_count": single_cover_count,
            "no_cover_count": no_cover_count,
            "fragile_shields": shield_fragility,
        }
        fallback_threats.append(base_item)
        if no_cover_count > 0 or single_cover_count > 0:
            threats.append(base_item)

    if threats:
        threats.sort(
            key=lambda item: (
                -item["no_cover_count"],
                -item["single_cover_count"],
                item["min_best_score"],
                item["avg_best_score"],
            )
        )
        return threats[:top_n]

    fallback_threats.sort(key=lambda item: (item["min_best_score"], item["avg_best_score"]))
    return fallback_threats[:top_n]


def build_target_map(
    row_labels: list[str],
    col_labels: list[str],
    matrices: list[list[list[int]]],
    team_indices: tuple[int, ...],
) -> list[dict[str, Any]]:
    target_map: list[dict[str, Any]] = []
    for col_idx, opponent_label in enumerate(col_labels):
        shield_best_scores: list[int] = []
        shield_best_members: list[str] = []
        for shield_idx, matrix in enumerate(matrices):
            best_score = -1
            best_member = ""
            for row_idx in team_indices:
                value = matrix[row_idx][col_idx]
                if value > best_score:
                    best_score = value
                    best_member = row_labels[row_idx]
            shield_best_scores.append(best_score)
            shield_best_members.append(best_member)

        min_score = min(shield_best_scores)
        score_range = max(shield_best_scores) - min_score
        confidence = "stable"
        if min_score < 620:
            confidence = "fragile"
        elif score_range > 170:
            confidence = "swingy"

        target_map.append(
            {
                "opponent_label": opponent_label,
                "shield_best_scores": shield_best_scores,
                "shield_best_members": shield_best_members,
                "confidence": confidence,
            }
        )

    return target_map


def build_core_role_recommendation(
    row_labels: list[str],
    col_labels: list[str],
    matrices: list[list[list[int]]],
    core_indices: tuple[int, ...],
    safety_by_row: list[float],
) -> dict[str, Any]:
    role_scores = {
        row_labels[row_idx]: _role_scores(row_idx, matrices, safety_by_row)
        for row_idx in core_indices
    }
    best_order = max(
        itertools.permutations(core_indices),
        key=lambda order: (
            role_scores[row_labels[order[0]]]["lead"]
            + role_scores[row_labels[order[1]]]["switch"]
            + role_scores[row_labels[order[2]]]["closer"],
            role_scores[row_labels[order[1]]]["switch"],
            role_scores[row_labels[order[0]]]["lead"],
            role_scores[row_labels[order[2]]]["closer"],
        ),
    )
    strategy, shared_weaknesses, shared_strengths = _classify_ordered_core(
        best_order, col_labels, matrices
    )

    return {
        "strategy": strategy,
        "recommended_order": [
            {"role": role, "label": row_labels[row_idx], "index": row_idx}
            for role, row_idx in zip(("lead", "switch", "closer"), best_order, strict=True)
        ],
        "role_scores": role_scores,
        "shared_weaknesses": shared_weaknesses,
        "shared_strengths": shared_strengths,
    }


def _role_scores(
    row_idx: int,
    matrices: list[list[list[int]]],
    safety_by_row: list[float],
) -> dict[str, float]:
    zero_shield = matrices[0][row_idx]
    one_shield = matrices[min(1, len(matrices) - 1)][row_idx]
    all_scores = [score for matrix in matrices for score in matrix[row_idx]]

    lead_score = _average(one_shield) - (25.0 * _hard_loss_rate(one_shield))
    switch_score = _average(all_scores) + safety_by_row[row_idx]
    closer_score = _average(zero_shield) + (20.0 * _dominate_rate(zero_shield))
    return {
        "lead": round(lead_score, 3),
        "switch": round(switch_score, 3),
        "closer": round(closer_score, 3),
    }


def _classify_ordered_core(
    order: tuple[int, ...],
    col_labels: list[str],
    matrices: list[list[list[int]]],
) -> tuple[str, list[str], list[str]]:
    lead_idx, switch_idx, closer_idx = order
    back_weaknesses = _shared_matchups(switch_idx, closer_idx, col_labels, matrices, upper_bound=450)
    back_strengths = _shared_matchups(switch_idx, closer_idx, col_labels, matrices, lower_bound=600)
    lead_closer_weaknesses = _shared_matchups(lead_idx, closer_idx, col_labels, matrices, upper_bound=450)
    lead_closer_strengths = _shared_matchups(lead_idx, closer_idx, col_labels, matrices, lower_bound=600)

    if len(back_weaknesses) >= 2 or len(back_strengths) >= 2:
        return "ABB", back_weaknesses, back_strengths
    if len(lead_closer_weaknesses) >= 2 or len(lead_closer_strengths) >= 2:
        return "ABA", lead_closer_weaknesses, lead_closer_strengths
    return "ABC", [], []


def _shared_matchups(
    first_idx: int,
    second_idx: int,
    col_labels: list[str],
    matrices: list[list[list[int]]],
    *,
    upper_bound: int | None = None,
    lower_bound: int | None = None,
) -> list[str]:
    shared: list[str] = []
    for col_idx, col_label in enumerate(col_labels):
        first = _average([matrix[first_idx][col_idx] for matrix in matrices])
        second = _average([matrix[second_idx][col_idx] for matrix in matrices])
        if upper_bound is not None and first < upper_bound and second < upper_bound:
            shared.append(col_label)
        if lower_bound is not None and first > lower_bound and second > lower_bound:
            shared.append(col_label)
    return shared


def _average(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _hard_loss_rate(values: list[int]) -> float:
    return sum(1 for value in values if value < 450) / len(values) if values else 0.0


def _dominate_rate(values: list[int]) -> float:
    return sum(1 for value in values if value > 650) / len(values) if values else 0.0


def to_team_members(
    team_indices: tuple[int, ...],
    row_labels: list[str],
    pokemon_types: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    members: list[dict[str, Any]] = []
    for row_idx in team_indices:
        species = parse_species(row_labels[row_idx])
        members.append(
            {
                "index": row_idx,
                "label": row_labels[row_idx],
                "species": species,
                "base_species": parse_base_species(species),
                "types": list(pokemon_types.get(species, ())),
            }
        )
    return members
