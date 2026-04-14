from pathlib import Path

from pogo_team_optimizer.infrastructure.repositories.battle_frontier_points_repository import (
    CsvBattleFrontierPointsRepository,
)


def test_battle_frontier_points_repository_reads_points(tmp_path) -> None:
    points_path = tmp_path / "bfmaster_cycle_points.csv"
    points_path.write_text(
        "species,points\nGroudon,3\nCharizard (Mega Y),4\n",
        encoding="utf-8",
    )

    repository = CsvBattleFrontierPointsRepository(str(points_path))

    assert repository.get_points("Groudon") == 3
    assert repository.get_points("Charizard (Mega Y)") == 4


def test_battle_frontier_points_repository_returns_zero_for_missing_species(tmp_path) -> None:
    points_path = tmp_path / "bfmaster_cycle_points.csv"
    points_path.write_text("species,points\nGroudon,3\n", encoding="utf-8")

    repository = CsvBattleFrontierPointsRepository(str(points_path))

    assert repository.get_points("Lugia") == 0


def test_checked_in_bfmaster_points_csv_exists_and_uses_normalized_species_names() -> None:
    repository = CsvBattleFrontierPointsRepository("data/battle_frontier/bfmaster_cycle_points.csv")

    assert Path("data/battle_frontier/bfmaster_cycle_points.csv").exists()
    assert repository.get_points("Groudon") == 3
    assert repository.get_points("Kyurem (White)") == 4
    assert repository.get_points("Charizard (Mega Y)") == 4
    assert repository.get_points("Swampert (Mega)") == 5
    assert repository.get_points("Metagross") == 3
    assert repository.get_points("Metagross (Shadow)") == 3
    assert repository.get_points("Tyranitar") == 2
    assert repository.get_points("Tyranitar (Shadow)") == 2
    assert repository.get_points("Dialga (Shadow)") == 2
    assert repository.get_points("Palkia (Shadow)") == 2
    assert repository.get_points("Lugia (Shadow)") == 2
    assert repository.get_points("Ho-Oh (Shadow)") == 2
    assert repository.get_points("Rhyperior (Shadow)") == 2
    assert repository.get_points("Gyarados (Shadow)") == 1
    assert repository.get_points("Garchomp (Shadow)") == 1
    assert repository.get_points("Heatran (Shadow)") == 1
    assert repository.get_points("Giratina (Altered) (Shadow)") == 1
    assert repository.get_points("Groudon (Shadow)") == 3
    assert repository.get_points("Kyogre (Shadow)") == 3
    assert repository.get_points("Moltres (Shadow)") == 1
    assert repository.get_points("Togekiss") == 0
    assert repository.get_points("Zacian (Crowned Sword)") == 5
