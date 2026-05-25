from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

from pogo_team_optimizer.application.normalization import parse_species
from pogo_team_optimizer.domain.interfaces import RankingsRepository
from pogo_team_optimizer.domain.models import RankingCategory, RankingProfile, RankingRow


class CsvRankingsRepository(RankingsRepository):
    def __init__(self, ranking_paths: Mapping[RankingCategory | str, str]) -> None:
        self.ranking_paths: dict[RankingCategory, Path] = {}
        for category, path in ranking_paths.items():
            self.ranking_paths[self._parse_category(category)] = Path(path)

    def load(self) -> RankingProfile:
        scores_by_category: dict[RankingCategory, dict[str, RankingRow]] = {}
        for category, path in self.ranking_paths.items():
            scores_by_category[category] = self._load_category(path)
        return RankingProfile(scores_by_category=scores_by_category)

    def _load_category(self, path: Path) -> dict[str, RankingRow]:
        rows_by_species: dict[str, RankingRow] = {}
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                species_text = row.get("Pokemon")
                score_text = row.get("Score")
                if not species_text or not score_text:
                    continue
                try:
                    score = float(score_text)
                except ValueError:
                    continue
                species = parse_species(species_text)
                if not species:
                    continue
                rows_by_species[species] = RankingRow(species=species, score=score)
        return rows_by_species

    def _parse_category(self, category: RankingCategory | str) -> RankingCategory:
        if isinstance(category, RankingCategory):
            return category
        try:
            return RankingCategory(category)
        except ValueError as error:
            supported = ", ".join(category.value for category in RankingCategory)
            raise ValueError(
                f"Unsupported ranking category '{category}'. Expected one of: {supported}"
            ) from error
