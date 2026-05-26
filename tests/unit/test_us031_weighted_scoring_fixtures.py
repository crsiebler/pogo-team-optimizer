from pathlib import Path

import pytest

from pogo_team_optimizer.application.ranking_pools import build_ranking_pools
from pogo_team_optimizer.application.scoring import calculate_ranking_aware_roster_score
from pogo_team_optimizer.application.optimizer import TeamOptimizer
from pogo_team_optimizer.cli.main import build_parser
from pogo_team_optimizer.domain.models import RankingCategory
from pogo_team_optimizer.infrastructure.repositories.csv_matrix_repository import (
    CsvSimulationMatrixRepository,
)
from pogo_team_optimizer.infrastructure.repositories.csv_rankings_repository import (
    CsvRankingsRepository,
)
from pogo_team_optimizer.infrastructure.repositories.move_json_repository import MoveJsonRepository
from pogo_team_optimizer.infrastructure.repositories.pokemon_json_repository import PokemonJsonRepository


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "us031_weighted_scoring"


def _ranking_paths(prefix: str = "active") -> dict[RankingCategory, str]:
    return {
        category: str(FIXTURE_ROOT / "rankings" / f"{prefix}_{category.value}.csv")
        for category in RankingCategory
    }


def _matrix_paths() -> list[str]:
    return [
        str(FIXTURE_ROOT / "matrices" / f"weighted_fixture_{shield}-shield.csv")
        for shield in (0, 1, 2)
    ]


def test_us031_ranking_fixtures_load_all_categories_with_edge_cases() -> None:
    profile = CsvRankingsRepository(_ranking_paths()).load()

    assert set(profile.scores_by_category) == set(RankingCategory)
    assert profile.scores_by_category[RankingCategory.OVERALL]["Clodsire"].score == 88.0
    assert profile.scores_by_category[RankingCategory.OVERALL]["Clodsire"].normalized_score is None
    assert profile.scores_by_category[RankingCategory.LEADS].get("Missingmon") is None
    assert profile.scores_by_category[RankingCategory.SWITCHES]["Lickilicky"].score == 90.0
    assert profile.scores_by_category[RankingCategory.SWITCHES]["Dragonite"].score == 90.0


def test_us031_type_move_and_matrix_fixtures_are_minimal_and_loadable() -> None:
    pokemon_repo = PokemonJsonRepository(str(FIXTURE_ROOT / "pokemon.json"))
    move_repo = MoveJsonRepository(str(FIXTURE_ROOT / "moves.json"))
    row_labels, col_labels, matrices = CsvSimulationMatrixRepository(_matrix_paths()).load()

    assert pokemon_repo.get_types("Clodsire") == ("poison", "ground")
    assert pokemon_repo.get_base_stats("Lickilicky") == (161, 181, 242)
    assert move_repo.get_move_type("MUD_SHOT") == "ground"
    assert move_repo.get_move_type("BS") == "normal"
    assert row_labels[:4] == [
        "Aegislash",
        "Blastoise",
        "Clodsire 0/14/13",
        "Clodsire 1/15/14",
    ]
    assert col_labels == [
        "Lickilicky",
        "Clodsire 0/14/13",
        "Dragonite (Shadow)",
        "Talonflame",
        "Venusaur",
        "Missingmon",
    ]
    assert len(matrices) == 3


def test_us031_fixture_profiles_build_active_full_meta_and_top_threat_pools() -> None:
    active_profile = CsvRankingsRepository(_ranking_paths()).load()
    full_meta_profile = CsvRankingsRepository(
        {RankingCategory.OVERALL: str(FIXTURE_ROOT / "rankings" / "full_meta_overall.csv")}
    ).load()
    row_labels, col_labels, _ = CsvSimulationMatrixRepository(_matrix_paths()).load()

    pools = build_ranking_pools(
        active_profile=active_profile,
        full_meta_profile=full_meta_profile,
        row_labels=row_labels,
        col_labels=col_labels,
        top_threat_count=4,
    )

    assert [entry.species for entry in pools.active_meta[:4]] == [
        "Lickilicky",
        "Dragonite (Shadow)",
        "Clodsire",
        "Talonflame",
    ]
    assert [entry.species for entry in pools.full_meta[:3]] == [
        "Talonflame",
        "Venusaur",
        "Lickilicky",
    ]
    assert [entry.matrix_index for entry in pools.top_threats] == [0, 2, 1, 3]
    assert pools.active_meta[-1].species == "Missingmon"
    assert pools.active_meta[-1].ranking_score is None


def test_us031_fixture_weighted_score_prefers_top_threat_coverage() -> None:
    _, _, matrices = CsvSimulationMatrixRepository(_matrix_paths()).load()

    top_threat_team = calculate_ranking_aware_roster_score(
        team_indices=[0, 1, 2],
        matrices=matrices,
        bulk_by_row=[220.0] * 12,
        top_threat_indices=(0, 1, 2),
        full_meta_indices=(0, 1, 2, 3, 4, 5),
    )
    no_top_threat_answers_team = calculate_ranking_aware_roster_score(
        team_indices=[3, 4, 5],
        matrices=matrices,
        bulk_by_row=[220.0] * 12,
        top_threat_indices=(0, 1, 2),
        full_meta_indices=(0, 1, 2, 3, 4, 5),
    )

    assert top_threat_team.final_score > no_top_threat_answers_team.final_score


def test_us031_fixture_optimizer_prefers_multiple_viable_lineups_with_explicit_seed() -> None:
    row_labels, col_labels, matrices = CsvSimulationMatrixRepository(_matrix_paths()).load()
    optimizer = TeamOptimizer(
        row_labels=row_labels,
        col_labels=col_labels,
        matrices=matrices,
        bulk_by_row=[220.0] * len(row_labels),
        seed=31,
    )
    one_lineup_team = [0, 1, 2, 3, 4, 5]
    depth_team = [6, 7, 8, 9, 10, 11]

    assert (
        optimizer._score_team_lineups(one_lineup_team).best_lineup_score
        > optimizer._score_team_lineups(depth_team).best_lineup_score
    )
    assert optimizer._comparison_key(
        depth_team,
        optimizer._score_team(depth_team),
        safety_floor=None,
        min_safe_members=0,
        safe_member_floor=90.0,
    ) > optimizer._comparison_key(
        one_lineup_team,
        optimizer._score_team(one_lineup_team),
        safety_floor=None,
        min_safe_members=0,
        safe_member_floor=90.0,
    )


def test_us031_crucible_remains_removed_from_cli_choices() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit, match="2"):
        parser.parse_args(["--meta", "crucible"])
