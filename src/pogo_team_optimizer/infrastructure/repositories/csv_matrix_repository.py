from __future__ import annotations

import csv
from pathlib import Path

from pogo_team_optimizer.domain.interfaces import MatchupValue, SimulationMatrixRepository


NON_MATCHUP_COLUMN_NAMES = {
    "wins",
    "losses",
    "draws",
    "average",
    "fast move",
    "charged move 1",
    "charged move 2",
    "score",
}


class CsvSimulationMatrixRepository(SimulationMatrixRepository):
    def __init__(self, matrix_files: list[str]) -> None:
        self.matrix_files = [Path(path) for path in matrix_files]

    def load(self) -> tuple[list[str], list[str], list[list[list[MatchupValue]]]]:
        row_labels: list[str] | None = None
        col_labels: list[str] | None = None
        matrices: list[list[list[MatchupValue]]] = []

        for file_path in self.matrix_files:
            with file_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            matchup_col_indices = _matchup_column_indices(rows[0])
            if not matchup_col_indices:
                raise ValueError(f"No matchup columns found in {file_path}")
            current_cols = [rows[0][col_idx] for col_idx in matchup_col_indices]
            current_rows: list[str] = []
            matrix: list[list[MatchupValue]] = []
            for row in rows[1:]:
                if not row or not row[0].strip():
                    continue
                current_rows.append(row[0])
                matrix.append([_parse_matchup_value(row, col_idx) for col_idx in matchup_col_indices])

            if col_labels is None:
                col_labels = current_cols
            elif col_labels != current_cols:
                raise ValueError(f"Column labels do not match in {file_path}")

            if row_labels is None:
                row_labels = current_rows
            elif row_labels != current_rows:
                raise ValueError(f"Row labels do not match in {file_path}")

            matrices.append(matrix)

        if row_labels is None or col_labels is None:
            raise ValueError("No simulation data loaded")

        return row_labels, col_labels, matrices


def _matchup_column_indices(headers: list[str]) -> list[int]:
    return [
        col_idx
        for col_idx, header in enumerate(headers[1:], start=1)
        if header.strip().lower() not in NON_MATCHUP_COLUMN_NAMES
    ]


def _parse_matchup_value(row: list[str], col_idx: int) -> MatchupValue:
    if col_idx >= len(row):
        return None
    value = row[col_idx].strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
