from __future__ import annotations

import csv
from pathlib import Path

from pogo_team_optimizer.domain.interfaces import SimulationMatrixRepository


class CsvSimulationMatrixRepository(SimulationMatrixRepository):
    def __init__(self, matrix_files: list[str]) -> None:
        self.matrix_files = [Path(path) for path in matrix_files]

    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        row_labels: list[str] | None = None
        col_labels: list[str] | None = None
        matrices: list[list[list[int]]] = []

        for file_path in self.matrix_files:
            with file_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            current_cols = rows[0][1:-4]
            current_rows: list[str] = []
            matrix: list[list[int]] = []
            for row in rows[1:]:
                if not row or not row[0].strip():
                    continue
                current_rows.append(row[0])
                matrix.append([int(value) for value in row[1 : 1 + len(current_cols)]])

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
