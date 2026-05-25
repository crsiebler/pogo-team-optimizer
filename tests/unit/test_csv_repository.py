import csv

from pogo_team_optimizer.infrastructure.repositories.csv_matrix_repository import (
    CsvSimulationMatrixRepository,
)


def test_csv_repository_loads_three_scenarios(tmp_path) -> None:
    simulations = tmp_path / "simulations"
    simulations.mkdir()
    headers = ["", "A", "B", "Wins", "Losses", "Draws", "Average"]
    rows = [
        ["Mon1", "600", "400", "1", "1", "0", "500"],
        ["Mon2", "400", "600", "1", "1", "0", "500"],
    ]

    for shield in [0, 1, 2]:
        file_path = simulations / f"great_{shield}-shield.csv"
        with file_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)

    repo = CsvSimulationMatrixRepository(
        [
            str(simulations / "great_0-shield.csv"),
            str(simulations / "great_1-shield.csv"),
            str(simulations / "great_2-shield.csv"),
        ]
    )
    row_labels, col_labels, matrices = repo.load()

    assert row_labels == ["Mon1", "Mon2"]
    assert col_labels == ["A", "B"]
    assert len(matrices) == 3
    assert matrices[0][0][0] == 600
