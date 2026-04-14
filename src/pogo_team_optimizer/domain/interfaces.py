from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SimulationMatrixRepository(ABC):
    @abstractmethod
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        """Return row labels, column labels, and 3 shield matrices."""


class PokemonRepository(ABC):
    @abstractmethod
    def get_types(self, species_name: str) -> tuple[str, ...]:
        """Return pokemon types by display species name."""

    @abstractmethod
    def get_base_stats(self, species_name: str) -> tuple[int, int, int] | None:
        """Return (atk, def, hp) for a species when available."""


class SwitchRankingsRepository(ABC):
    @abstractmethod
    def get_switch_score(self, species_name: str) -> float | None:
        """Return PvPoke switch score for a species when available."""


class AnalysisExporter(ABC):
    @abstractmethod
    def export(self, result: dict[str, Any], output_path: str | None = None) -> str | None:
        """Export analysis result and optionally return rendered text."""
