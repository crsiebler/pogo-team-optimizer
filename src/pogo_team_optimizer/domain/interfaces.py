from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pogo_team_optimizer.domain.models import RankingProfile

MatchupValue = int | None


class SimulationMatrixRepository(ABC):
    @abstractmethod
    def load(self) -> tuple[list[str], list[str], list[list[list[MatchupValue]]]]:
        """Return row labels, column labels, and 3 shield matrices."""


class PokemonRepository(ABC):
    @abstractmethod
    def get_types(self, species_name: str) -> tuple[str, ...]:
        """Return pokemon types by display species name."""

    @abstractmethod
    def get_base_stats(self, species_name: str) -> tuple[int, int, int] | None:
        """Return (atk, def, hp) for a species when available."""


class MoveRepository(ABC):
    @abstractmethod
    def get_move_type(self, move_token: str) -> str | None:
        """Return move type by abbreviation or move id when available."""


class TypeEffectivenessRepository(ABC):
    @abstractmethod
    def load(self) -> dict[str, dict[str, float]]:
        """Return attack type to defender type effectiveness multipliers."""


class SwitchRankingsRepository(ABC):
    @abstractmethod
    def get_switch_score(self, species_name: str) -> float | None:
        """Return PvPoke switch score for a species when available."""


class RankingsRepository(ABC):
    @abstractmethod
    def load(self) -> RankingProfile:
        """Return PvPoke ranking scores grouped by category."""


class BattleFrontierPointsRepository(ABC):
    @abstractmethod
    def get_points(self, species_name: str) -> int:
        """Return Battle Frontier point cost for a species, defaulting missing entries to 0."""


class AnalysisExporter(ABC):
    @abstractmethod
    def export(self, result: dict[str, Any], output_path: str | None = None) -> str | None:
        """Export analysis result and optionally return rendered text."""
