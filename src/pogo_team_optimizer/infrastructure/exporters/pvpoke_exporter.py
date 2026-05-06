from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pogo_team_optimizer.domain.interfaces import AnalysisExporter


def _build_fallback_aliases(move_id: str, move_name: str | None) -> set[str]:
    aliases: set[str] = set()
    normalized_id = move_id.upper()
    aliases.add(normalized_id)

    parts = normalized_id.split("_")
    aliases.add("".join(part[0] for part in parts if part))
    if len(parts) == 2 and parts[0] and len(parts[1]) >= 2:
        aliases.add(parts[0][0] + parts[1][:2])
    if len(parts) == 3 and all(parts):
        aliases.add(parts[0][0] + parts[1][0] + parts[2][0])

    if move_name:
        words = [w for w in re.split(r"[^A-Za-z0-9]+", move_name.upper()) if w]
        if words:
            aliases.add("".join(word[0] for word in words))
        if len(words) == 2 and len(words[0]) >= 3 and words[1]:
            aliases.add(words[0][:3] + words[1][0])

    return aliases


class PvpokeExporter(AnalysisExporter):
    def __init__(self, pokemon_path: str, moves_path: str) -> None:
        self.pokemon_path = Path(pokemon_path)
        self.moves_path = Path(moves_path)
        self._species_ids: set[str] = set()
        self._species_ids_by_name: dict[str, list[str]] = {}
        self._species_tags_by_id: dict[str, set[str]] = {}
        self._legal_fast_by_id: dict[str, set[str]] = {}
        self._legal_charged_by_id: dict[str, set[str]] = {}
        self._move_alias_to_ids: dict[str, set[str]] = {}
        self._load_data()

    def _load_data(self) -> None:
        with self.pokemon_path.open(encoding="utf-8") as handle:
            pokemon_data = json.load(handle)
        for item in pokemon_data:
            species = item.get("speciesName")
            species_id = item.get("speciesId")
            if not isinstance(species, str) or not isinstance(species_id, str):
                continue
            self._species_ids.add(species_id)
            self._species_ids_by_name.setdefault(species, []).append(species_id)
            tags = item.get("tags", [])
            self._species_tags_by_id[species_id] = set(tags) if isinstance(tags, list) else set()
            self._legal_fast_by_id[species_id] = set(item.get("fastMoves", []))
            self._legal_charged_by_id[species_id] = set(item.get("chargedMoves", []))

        with self.moves_path.open(encoding="utf-8") as handle:
            moves_data = json.load(handle)
        for move in moves_data:
            move_id = move.get("moveId")
            if not isinstance(move_id, str):
                continue
            aliases: set[str] = {move_id.upper()}
            abbreviation = move.get("abbreviation")
            if isinstance(abbreviation, str) and abbreviation:
                aliases.add(abbreviation.upper())
            else:
                aliases.update(_build_fallback_aliases(move_id, move.get("name")))

            for alias in aliases:
                self._move_alias_to_ids.setdefault(alias, set()).add(move_id)

    def _parse_label(self, label: str) -> tuple[str, str, str, str, tuple[int, int, int] | None]:
        stripped = label.strip()
        ivs: tuple[int, int, int] | None = None
        iv_match = re.search(r"\s+(?P<atk>\d+)/(?P<def>\d+)/(?P<hp>\d+)$", stripped)
        if iv_match:
            ivs = (
                int(iv_match.group("atk")),
                int(iv_match.group("def")),
                int(iv_match.group("hp")),
            )
            stripped = stripped[: iv_match.start()].strip()
        match = re.match(r"^(?P<species>.+?)\s+(?P<moves>[A-Za-z0-9]+\+[^\s]+)$", stripped)
        if not match:
            raise ValueError(f"Unable to parse moveset from label: {label}")

        species = match.group("species").strip()
        moveset = match.group("moves")
        fast_token, charged_tokens = moveset.split("+", maxsplit=1)
        charged_parts = charged_tokens.split("/")
        if len(charged_parts) != 2:
            raise ValueError(f"Expected two charged moves in label: {label}")
        return species, fast_token.upper(), charged_parts[0].upper(), charged_parts[1].upper(), ivs

    def _parse_species_parts(self, species: str) -> tuple[str, list[str], bool]:
        groups = re.findall(r"\(([^)]+)\)", species)
        is_shadow = any(group.strip().lower() == "shadow" for group in groups)
        forms = [group.strip().lower() for group in groups if group.strip().lower() != "shadow"]
        base_name = re.sub(r"\s*\([^)]*\)", "", species).strip()
        return base_name, forms, is_shadow

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        slug = re.sub(r"_+", "_", slug)
        return slug

    def _build_species_id(self, species: str) -> str:
        base_name, forms, is_shadow = self._parse_species_parts(species)
        base_slug = self._slugify(base_name)
        form_slugs = [self._slugify(form) for form in forms]
        parts = [base_slug]
        parts.extend(form_slugs)
        if is_shadow and (not parts or parts[-1] != "shadow"):
            parts.append("shadow")
        return "_".join(part for part in parts if part)

    def _resolve_species_id(self, species: str, label: str) -> str:
        generated_id = self._build_species_id(species)
        if generated_id in self._species_ids:
            return generated_id

        candidates = self._species_ids_by_name.get(species, [])
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            non_duplicate = [
                species_id
                for species_id in candidates
                if not {"duplicate", "duplicate1500"}
                & self._species_tags_by_id.get(species_id, set())
            ]
            if len(non_duplicate) == 1:
                return non_duplicate[0]
            if generated_id in non_duplicate:
                return generated_id

        raise ValueError(
            f"Unable to resolve speciesId for species '{species}' from label '{label}'. "
            f"Generated '{generated_id}'."
        )

    def _resolve_move(
        self,
        token: str,
        legal_moves: set[str],
        species: str,
        label: str,
    ) -> str:
        candidates = self._move_alias_to_ids.get(token, set())
        legal_candidates = sorted(move_id for move_id in candidates if move_id in legal_moves)

        if len(legal_candidates) == 1:
            return legal_candidates[0]
        if len(legal_candidates) > 1:
            raise ValueError(
                "Ambiguous move token "
                f"'{token}' for species '{species}' in label '{label}'. "
                f"Candidates: {', '.join(legal_candidates)}"
            )

        raise ValueError(
            f"Unresolved move token '{token}' for species '{species}' in label '{label}'."
        )

    def export(self, result: dict[str, Any], output_path: str | None = None) -> str | None:
        lines: list[str] = []
        members = result.get("recommended_team", {}).get("members", [])
        for member in members:
            label = member["label"]
            parsed_species, fast_token, charged1_token, charged2_token, ivs = self._parse_label(label)
            species_id = self._resolve_species_id(parsed_species, label)

            legal_fast = self._legal_fast_by_id.get(species_id, set())
            legal_charged = self._legal_charged_by_id.get(species_id, set())

            fast_move = self._resolve_move(fast_token, legal_fast, parsed_species, label)
            charged1 = self._resolve_move(charged1_token, legal_charged, parsed_species, label)
            charged2 = self._resolve_move(charged2_token, legal_charged, parsed_species, label)
            fields = [species_id, fast_move, charged1, charged2]
            if ivs is not None:
                fields.extend(str(value) for value in ivs)
            lines.append(",".join(fields))

        rendered = "\n".join(lines)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(rendered)
            return None
        return rendered
