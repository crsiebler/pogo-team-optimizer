from pogo_team_optimizer.application.use_case import AnalyzeMetaUseCase
from pogo_team_optimizer.application.optimizer import TeamOptimizer
from pogo_team_optimizer.application.normalization import parse_species
from pogo_team_optimizer.infrastructure.repositories.battle_frontier_points_repository import (
    CsvBattleFrontierPointsRepository,
)
from pogo_team_optimizer.infrastructure.repositories.csv_matrix_repository import (
    CsvSimulationMatrixRepository,
)
from pogo_team_optimizer.infrastructure.repositories.csv_switch_rankings_repository import (
    CsvSwitchRankingsRepository,
)
from pogo_team_optimizer.infrastructure.repositories.pokemon_json_repository import (
    PokemonJsonRepository,
)


def test_use_case_returns_required_sections() -> None:
    use_case = AnalyzeMetaUseCase(
        simulation_repository=CsvSimulationMatrixRepository(
            [
                "data/simulations/great_0-shield.csv",
                "data/simulations/great_1-shield.csv",
                "data/simulations/great_2-shield.csv",
            ]
        ),
        pokemon_repository=PokemonJsonRepository("data/pokemon.json"),
    )

    result = use_case.execute(top_threats=5, top_lineups=3, seed=7, restarts=10)

    assert "recommended_team" in result
    assert len(result["recommended_team"]["members"]) == 6
    assert len(result["coverage"]) == 3
    assert 0 < len(result["threats"]) <= 5
    assert len(result["recommended_lineups"]) == 3
    assert result["safe_cores"] == []
    assert len(result["target_map"]) > 0
    assert "safety_score" in result["recommended_team"]["metrics"]
    assert "safety_pool_mean" in result["recommended_team"]["metrics"]
    assert result["recommended_team"]["metrics"]["safety_priority"] == "medium"


def test_bfmaster_use_case_returns_legal_team() -> None:
    use_case = AnalyzeMetaUseCase(
        simulation_repository=CsvSimulationMatrixRepository(
            [
                "data/simulations/bfmaster_0-shield.csv",
                "data/simulations/bfmaster_1-shield.csv",
                "data/simulations/bfmaster_2-shield.csv",
            ]
        ),
        pokemon_repository=PokemonJsonRepository("data/pokemon.json"),
        switch_rankings_repository=CsvSwitchRankingsRepository(
            "data/rankings/cp10000_battlefrontiermaster_switches_rankings.csv"
        ),
        battle_frontier_points_repository=CsvBattleFrontierPointsRepository(
            "data/battle_frontier/bfmaster_cycle_points.csv"
        ),
    )

    result = use_case.execute(top_threats=5, top_lineups=3, seed=7, restarts=10)

    team_members = result["recommended_team"]["members"]
    metrics = result["recommended_team"]["metrics"]

    assert len(team_members) == 6
    assert len({member["base_species"] for member in team_members}) == 6
    assert metrics["battle_frontier_points_used"] <= metrics["battle_frontier_max_points"]
    assert (
        metrics["battle_frontier_five_point_members"]
        <= metrics["battle_frontier_max_five_point_members"]
    )
    assert metrics["battle_frontier_mega_members"] <= metrics["battle_frontier_max_mega_members"]


def test_bfmaster_points_schedule_marks_known_19_point_team_illegal() -> None:
    points_repository = CsvBattleFrontierPointsRepository(
        "data/battle_frontier/bfmaster_cycle_points.csv"
    )
    row_labels = [
        "Tyranitar 15/15/15",
        "Kyurem (White) 15/15/15",
        "Meloetta (Aria) 15/15/15",
        "Charizard (Mega Y) 15/15/15",
        "Metagross 15/15/15",
        "Groudon 15/15/15",
    ]
    col_labels = ["Kyogre 15/15/15"]
    matrices = [[[500] for _ in row_labels]]
    optimizer = TeamOptimizer(
        row_labels=row_labels,
        col_labels=col_labels,
        matrices=matrices,
        bulk_by_row=[1.0] * len(row_labels),
        battle_frontier_points_by_row=[
            points_repository.get_points(parse_species(label)) for label in row_labels
        ],
        seed=7,
    )

    illegal_team_indices = list(range(len(row_labels)))

    assert len(illegal_team_indices) == 6
    assert sum(optimizer.battle_frontier_points_by_row[idx] for idx in illegal_team_indices) == 19
    assert optimizer._is_team_legal(illegal_team_indices) is False
