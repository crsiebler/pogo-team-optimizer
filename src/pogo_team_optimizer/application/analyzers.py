from __future__ import annotations

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
) -> list[dict[str, Any]]:
    threats: list[dict[str, Any]] = []
    fallback_threats: list[dict[str, Any]] = []
    for col_idx, opponent_label in enumerate(col_labels):
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
