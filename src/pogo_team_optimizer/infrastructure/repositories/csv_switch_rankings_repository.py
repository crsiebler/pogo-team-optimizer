from pogo_team_optimizer.domain.interfaces import SwitchRankingsRepository
from pogo_team_optimizer.domain.models import RankingCategory
from pogo_team_optimizer.infrastructure.repositories.csv_rankings_repository import (
    CsvRankingsRepository,
)


class CsvSwitchRankingsRepository(SwitchRankingsRepository):
    def __init__(self, rankings_path: str) -> None:
        self._profile = CsvRankingsRepository(
            {RankingCategory.SWITCHES: rankings_path}
        ).load()

    def get_switch_score(self, species_name: str) -> float | None:
        return self._profile.get_score(RankingCategory.SWITCHES, species_name)
