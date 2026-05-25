from __future__ import annotations

import json
from pathlib import Path

from pogo_team_optimizer.domain.interfaces import TypeEffectivenessRepository


class TypeEffectivenessJsonRepository(TypeEffectivenessRepository):
    def __init__(self, type_effectiveness_path: str) -> None:
        self.type_effectiveness_path = Path(type_effectiveness_path)

    def load(self) -> dict[str, dict[str, float]]:
        with self.type_effectiveness_path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        effectiveness: dict[str, dict[str, float]] = {}
        for attack_type, defender_values in data.items():
            if not isinstance(attack_type, str) or not isinstance(defender_values, dict):
                continue
            effectiveness[attack_type] = {
                defender_type: float(multiplier)
                for defender_type, multiplier in defender_values.items()
                if isinstance(defender_type, str) and isinstance(multiplier, (int, float))
            }
        return effectiveness
