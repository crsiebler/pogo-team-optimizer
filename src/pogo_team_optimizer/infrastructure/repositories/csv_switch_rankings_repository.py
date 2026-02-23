from __future__ import annotations

import csv
from pathlib import Path

from pogo_team_optimizer.domain.interfaces import SwitchRankingsRepository


class CsvSwitchRankingsRepository(SwitchRankingsRepository):
    def __init__(self, rankings_path: str) -> None:
        self.rankings_path = Path(rankings_path)
        self._scores_by_species: dict[str, float] = {}

        with self.rankings_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                species = row.get("Pokemon")
                score_text = row.get("Score")
                if not species or not score_text:
                    continue
                try:
                    score = float(score_text)
                except ValueError:
                    continue
                self._scores_by_species[species.strip()] = score

    def get_switch_score(self, species_name: str) -> float | None:
        return self._scores_by_species.get(species_name)
