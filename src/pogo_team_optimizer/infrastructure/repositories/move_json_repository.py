from __future__ import annotations

import json
import re
from pathlib import Path

from pogo_team_optimizer.domain.interfaces import MoveRepository


def _fallback_aliases(move_id: str, move_name: str | None) -> set[str]:
    aliases = {move_id.upper()}
    if not move_name:
        return aliases

    words = [word for word in re.split(r"[^A-Za-z0-9]+", move_name.upper()) if word]
    if words:
        aliases.add("".join(word[0] for word in words))
    return aliases


class MoveJsonRepository(MoveRepository):
    def __init__(self, moves_path: str) -> None:
        self.moves_path = Path(moves_path)
        with self.moves_path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        self._type_by_token: dict[str, str] = {}
        for item in data:
            move_type = item.get("type")
            move_id = item.get("moveId")
            if not isinstance(move_type, str) or not isinstance(move_id, str):
                continue
            aliases = _fallback_aliases(move_id, item.get("name"))
            abbreviation = item.get("abbreviation")
            if isinstance(abbreviation, str):
                aliases.add(abbreviation.upper())
            for alias in aliases:
                self._type_by_token[alias] = move_type

    def get_move_type(self, move_token: str) -> str | None:
        return self._type_by_token.get(move_token.upper())
