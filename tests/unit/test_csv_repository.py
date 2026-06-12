import csv

import pytest

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


def test_csv_repository_ignores_summary_columns_by_header_name(tmp_path) -> None:
    simulations = tmp_path / "simulations"
    simulations.mkdir()
    headers = ["", " Wins ", "A", "Average", "B", "LOSSES", "Draws"]
    rows = [
        ["Mon1", "1", "610", "500", "410", "0", "0"],
        ["Mon2", "1", "390", "500", "620", "0", "0"],
    ]

    for shield in [0, 1, 2]:
        file_path = simulations / f"great_{shield}-shield.csv"
        with file_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)

    row_labels, col_labels, matrices = CsvSimulationMatrixRepository(
        [str(simulations / f"great_{shield}-shield.csv") for shield in [0, 1, 2]]
    ).load()

    assert row_labels == ["Mon1", "Mon2"]
    assert col_labels == ["A", "B"]
    assert matrices[0] == [[610, 410], [390, 620]]


def test_csv_repository_treats_blank_and_non_numeric_matchups_as_missing(tmp_path) -> None:
    simulations = tmp_path / "simulations"
    simulations.mkdir()
    headers = ["", "A", "B", "Wins", "Losses", "Draws", "Average"]
    rows = [
        ["Mon1", "", "410", "1", "0", "0", "500"],
        ["Mon2", "390", "N/A", "1", "0", "0", "500"],
        ["Mon3", "620", " ", "1", "0", "0", "500"],
    ]

    for shield in [0, 1, 2]:
        file_path = simulations / f"great_{shield}-shield.csv"
        with file_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)

    _, _, matrices = CsvSimulationMatrixRepository(
        [str(simulations / f"great_{shield}-shield.csv") for shield in [0, 1, 2]]
    ).load()

    assert matrices[0] == [[None, 410], [390, None], [620, None]]


def test_csv_repository_rejects_files_without_matchup_columns(tmp_path) -> None:
    simulations = tmp_path / "simulations"
    simulations.mkdir()
    file_path = simulations / "great_0-shield.csv"
    with file_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["", "Wins", "Losses", "Draws", "Average"])
        writer.writerow(["Mon1", "1", "0", "0", "500"])

    repo = CsvSimulationMatrixRepository([str(file_path)])

    with pytest.raises(ValueError, match="No matchup columns found"):
        repo.load()


def test_csv_repository_rejects_column_label_mismatch_after_summary_exclusion(tmp_path) -> None:
    simulations = tmp_path / "simulations"
    simulations.mkdir()
    first_file = simulations / "great_0-shield.csv"
    second_file = simulations / "great_1-shield.csv"

    with first_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["", "A", "Wins", "B", "Average"])
        writer.writerow(["Mon1", "600", "1", "400", "500"])
    with second_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["", "A", "Wins", "C", "Average"])
        writer.writerow(["Mon1", "600", "1", "400", "500"])

    repo = CsvSimulationMatrixRepository([str(first_file), str(second_file)])

    with pytest.raises(ValueError, match="Column labels do not match"):
        repo.load()


def test_csv_repository_rejects_row_label_mismatch_across_shields(tmp_path) -> None:
    simulations = tmp_path / "simulations"
    simulations.mkdir()
    first_file = simulations / "great_0-shield.csv"
    second_file = simulations / "great_1-shield.csv"
    headers = ["", "A", "B", "Wins", "Losses", "Draws", "Average"]

    with first_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows([
            ["Mon1", "600", "400", "1", "0", "0", "500"],
            ["Mon2", "400", "600", "1", "0", "0", "500"],
        ])
    with second_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerow(["Mon1", "600", "400", "1", "0", "0", "500"])

    repo = CsvSimulationMatrixRepository([str(first_file), str(second_file)])

    with pytest.raises(ValueError, match="Row labels do not match"):
        repo.load()
