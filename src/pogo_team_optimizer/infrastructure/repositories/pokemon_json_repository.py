from __future__ import annotations

import json
from pathlib import Path

from pogo_team_optimizer.domain.interfaces import PokemonRepository


class PokemonJsonRepository(PokemonRepository):
    def __init__(self, pokemon_path: str) -> None:
        self.pokemon_path = Path(pokemon_path)
        with self.pokemon_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        self._types_by_species: dict[str, tuple[str, ...]] = {
            item["speciesName"]: tuple(item.get("types", [])) for item in data
        }
        self._stats_by_species: dict[str, tuple[int, int, int]] = {}
        for item in data:
            species = item.get("speciesName")
            stats = item.get("baseStats")
            if not species or not isinstance(stats, dict):
                continue
            atk = stats.get("atk")
            defense = stats.get("def")
            hp = stats.get("hp")
            if isinstance(atk, int) and isinstance(defense, int) and isinstance(hp, int):
                self._stats_by_species[species] = (atk, defense, hp)

    def get_types(self, species_name: str) -> tuple[str, ...]:
        return self._types_by_species.get(species_name, tuple())

    def get_base_stats(self, species_name: str) -> tuple[int, int, int] | None:
        return self._stats_by_species.get(species_name)
