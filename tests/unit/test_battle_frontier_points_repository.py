from pathlib import Path

from pogo_team_optimizer.infrastructure.repositories.battle_frontier_points_repository import (
    CsvBattleFrontierPointsRepository,
)


def test_battle_frontier_points_repository_reads_points(tmp_path) -> None:
    points_path = tmp_path / "bfmaster_cycle_points.csv"
    points_path.write_text(
        "species,points\nGroudon,5\nCharizard (Mega X),3\n",
        encoding="utf-8",
    )

    repository = CsvBattleFrontierPointsRepository(str(points_path))

    assert repository.get_points("Groudon") == 5
    assert repository.get_points("Charizard (Mega X)") == 3


def test_battle_frontier_points_repository_returns_zero_for_missing_species(tmp_path) -> None:
    points_path = tmp_path / "bfmaster_cycle_points.csv"
    points_path.write_text("species,points\nGroudon,5\n", encoding="utf-8")

    repository = CsvBattleFrontierPointsRepository(str(points_path))

    assert repository.get_points("Lugia") == 0


def test_checked_in_bfmaster_points_csv_exists_and_uses_normalized_species_names() -> None:
    repository = CsvBattleFrontierPointsRepository("data/battle_frontier/bfmaster_cycle_points.csv")

    assert Path("data/battle_frontier/bfmaster_cycle_points.csv").exists()
    assert repository.get_points("Groudon") == 5
    assert repository.get_points("Charizard (Mega X)") == 3
