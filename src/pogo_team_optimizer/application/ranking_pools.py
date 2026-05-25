from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from pogo_team_optimizer.application.normalization import parse_base_species, parse_species
from pogo_team_optimizer.domain.models import RankingCategory, RankingProfile

MIN_PVPOKE_RANKING_SCORE = 0.0
MAX_PVPOKE_RANKING_SCORE = 100.0


@dataclass(frozen=True)
class RankingPoolEntry:
    label: str
    species: str
    base_species: str
    matrix_index: int
    ranking_score: float | None
    weight: float


@dataclass(frozen=True)
class RankingPools:
    active_meta: tuple[RankingPoolEntry, ...]
    full_meta: tuple[RankingPoolEntry, ...]
    top_threats: tuple[RankingPoolEntry, ...]


def build_ranking_pools(
    *,
    active_profile: RankingProfile | None,
    full_meta_profile: RankingProfile | None,
    row_labels: Sequence[str],
    col_labels: Sequence[str],
    top_threat_count: int,
    category: RankingCategory = RankingCategory.OVERALL,
) -> RankingPools:
    labels = col_labels if col_labels else row_labels
    active_entries = _build_pool_entries(labels, active_profile, category)
    full_meta_entries = (
        _build_pool_entries(labels, full_meta_profile, category)
        if full_meta_profile is not None
        else ()
    )
    top_threats = _with_weights(active_entries[: max(0, top_threat_count)])
    return RankingPools(
        active_meta=active_entries,
        full_meta=full_meta_entries,
        top_threats=top_threats,
    )


def _build_pool_entries(
    labels: Sequence[str],
    profile: RankingProfile | None,
    category: RankingCategory,
) -> tuple[RankingPoolEntry, ...]:
    best_by_base_species: dict[str, RankingPoolEntry] = {}
    for matrix_index, label in enumerate(labels):
        species = parse_species(label)
        if not species:
            continue
        base_species = parse_base_species(species)
        ranking_score = _get_finite_score(profile, category, species)
        entry = RankingPoolEntry(
            label=label,
            species=species,
            base_species=base_species,
            matrix_index=matrix_index,
            ranking_score=ranking_score,
            weight=0.0,
        )
        current = best_by_base_species.get(base_species)
        if current is None or _entry_preference_key(entry) > _entry_preference_key(current):
            best_by_base_species[base_species] = entry

    ordered_entries = sorted(best_by_base_species.values(), key=_pool_sort_key)
    return _with_weights(tuple(ordered_entries))


def _entry_preference_key(entry: RankingPoolEntry) -> tuple[int, float, int]:
    if entry.ranking_score is None:
        return (0, 0.0, -entry.matrix_index)
    return (1, entry.ranking_score, -entry.matrix_index)


def _pool_sort_key(entry: RankingPoolEntry) -> tuple[int, float, int, str]:
    if entry.ranking_score is None:
        return (1, 0.0, entry.matrix_index, entry.species)
    return (0, -entry.ranking_score, entry.matrix_index, entry.species)


def _get_finite_score(
    profile: RankingProfile | None,
    category: RankingCategory,
    species: str,
) -> float | None:
    if profile is None:
        return None
    score = profile.get_score(category, species)
    if (
        score is None
        or not math.isfinite(score)
        or score < MIN_PVPOKE_RANKING_SCORE
        or score > MAX_PVPOKE_RANKING_SCORE
    ):
        return None
    return score


def _with_weights(entries: tuple[RankingPoolEntry, ...]) -> tuple[RankingPoolEntry, ...]:
    if not entries:
        return ()
    positive_score_total = sum(
        entry.ranking_score for entry in entries if entry.ranking_score is not None and entry.ranking_score > 0
    )
    if positive_score_total <= 0:
        uniform_weight = 1.0 / len(entries)
        return tuple(
            RankingPoolEntry(
                label=entry.label,
                species=entry.species,
                base_species=entry.base_species,
                matrix_index=entry.matrix_index,
                ranking_score=entry.ranking_score,
                weight=uniform_weight,
            )
            for entry in entries
        )

    return tuple(
        RankingPoolEntry(
            label=entry.label,
            species=entry.species,
            base_species=entry.base_species,
            matrix_index=entry.matrix_index,
            ranking_score=entry.ranking_score,
            weight=(entry.ranking_score / positive_score_total)
            if entry.ranking_score is not None and entry.ranking_score > 0
            else 0.0,
        )
        for entry in entries
    )
