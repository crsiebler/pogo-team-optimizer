from __future__ import annotations

import csv
from pathlib import Path

from pogo_team_optimizer.domain.interfaces import BattleFrontierPointsRepository


class CsvBattleFrontierPointsRepository(BattleFrontierPointsRepository):
    def __init__(self, points_path: str) -> None:
        self.points_path = Path(points_path)
        self._points_by_species: dict[str, int] = {}

        with self.points_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                species = row.get("species")
                points_text = row.get("points")
                if not species or not points_text:
                    continue
                try:
                    points = int(points_text)
                except ValueError:
                    continue
                self._points_by_species[species.strip()] = points

    def get_points(self, species_name: str) -> int:
        return self._points_by_species.get(species_name, 0)
