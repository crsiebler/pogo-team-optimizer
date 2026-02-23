from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


DEFAULT_FORM_BY_BASE: dict[str, str] = {
    "morpeko": "full_belly",
}


def _normalize_level(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    try:
        parsed = float(stripped)
    except ValueError:
        return stripped
    if parsed.is_integer():
        return str(int(parsed))
    return f"{parsed:g}"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return re.sub(r"_+", "_", slug)


def _canonical_move_key(value: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()
    return re.sub(r"\s+", " ", normalized)


def _normalize_form_token(form: str) -> str:
    token = form.strip().lower()
    mapping = {
        "": "",
        "normal": "",
        "alola": "alolan",
        "alolan": "alolan",
        "galar": "galarian",
        "galarian": "galarian",
        "hisui": "hisuian",
        "hisuian": "hisuian",
        "paldea": "paldean",
        "paldean": "paldean",
    }
    if token in mapping:
        return mapping[token]
    return _slugify(token)


def _parse_species_name(species_name: str) -> tuple[str, str, bool]:
    groups = re.findall(r"\(([^)]+)\)", species_name)
    is_shadow = False
    forms: list[str] = []
    for group in groups:
        normalized = _normalize_form_token(group)
        if normalized == "shadow":
            is_shadow = True
            continue
        if normalized:
            forms.append(normalized)

    base_name = re.sub(r"\s*\([^)]*\)", "", species_name).strip()
    form_token = "_".join(forms)
    return _slugify(base_name), form_token, is_shadow


def _pick_best_species_id(
    candidates: list[str], species_tags_by_id: dict[str, set[str]]
) -> str | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    non_duplicate = [
        species_id
        for species_id in candidates
        if not ({"duplicate", "duplicate1500"} & species_tags_by_id.get(species_id, set()))
    ]
    if len(non_duplicate) == 1:
        return non_duplicate[0]
    if non_duplicate:
        return sorted(non_duplicate)[0]
    return sorted(candidates)[0]


def _build_move_lookup(moves_path: Path) -> dict[str, set[str]]:
    with moves_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    lookup: dict[str, set[str]] = {}
    for item in data:
        move_id = item.get("moveId")
        if not isinstance(move_id, str):
            continue

        for key in {move_id.upper(), _canonical_move_key(move_id)}:
            if key:
                lookup.setdefault(key, set()).add(move_id)

        abbreviation = item.get("abbreviation")
        if isinstance(abbreviation, str) and abbreviation.strip():
            for key in {abbreviation.strip().upper(), _canonical_move_key(abbreviation.strip())}:
                if key:
                    lookup.setdefault(key, set()).add(move_id)

        name = item.get("name")
        if isinstance(name, str) and name.strip():
            for key in {name.strip().upper(), _canonical_move_key(name.strip())}:
                if key:
                    lookup.setdefault(key, set()).add(move_id)

            base_name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
            if base_name and base_name != name.strip():
                for key in {base_name.upper(), _canonical_move_key(base_name)}:
                    if key:
                        lookup.setdefault(key, set()).add(move_id)

        if move_id.startswith("WEATHER_BALL_"):
            for key in {"WEATHER_BALL", "WEATHER BALL"}:
                lookup.setdefault(key, set()).add(move_id)

    return lookup


def _build_species_lookup(
    pokemon_path: Path,
) -> tuple[
    dict[tuple[str, str, bool], list[str]],
    dict[tuple[str, bool], list[str]],
    dict[str, set[str]],
    dict[str, set[str]],
    dict[str, set[str]],
]:
    with pokemon_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    species_ids_by_key: dict[tuple[str, str, bool], list[str]] = {}
    species_ids_by_base_shadow: dict[tuple[str, bool], list[str]] = {}
    legal_fast_by_species_id: dict[str, set[str]] = {}
    legal_charged_by_species_id: dict[str, set[str]] = {}
    species_tags_by_id: dict[str, set[str]] = {}

    for item in data:
        species_name = item.get("speciesName")
        species_id = item.get("speciesId")
        if not isinstance(species_name, str) or not isinstance(species_id, str):
            continue

        base_key, form_token, is_shadow = _parse_species_name(species_name)
        key = (base_key, form_token, is_shadow)
        species_ids_by_key.setdefault(key, []).append(species_id)
        species_ids_by_base_shadow.setdefault((base_key, is_shadow), []).append(species_id)
        fast_moves = item.get("fastMoves", [])
        charged_moves = item.get("chargedMoves", [])
        legal_fast_by_species_id[species_id] = (
            set(fast_moves) if isinstance(fast_moves, list) else set()
        )
        legal_charged_by_species_id[species_id] = (
            set(charged_moves) if isinstance(charged_moves, list) else set()
        )

        tags = item.get("tags", [])
        species_tags_by_id[species_id] = set(tags) if isinstance(tags, list) else set()

    return (
        species_ids_by_key,
        species_ids_by_base_shadow,
        legal_fast_by_species_id,
        legal_charged_by_species_id,
        species_tags_by_id,
    )


def _resolve_species_id(
    name: str,
    form: str,
    shadow_purified: str,
    species_ids_by_key: dict[tuple[str, str, bool], list[str]],
    species_ids_by_base_shadow: dict[tuple[str, bool], list[str]],
    species_tags_by_id: dict[str, set[str]],
) -> str | None:
    base_key = _slugify(name)
    form_token = _normalize_form_token(form)
    is_shadow = shadow_purified.strip() == "1"
    default_form_token = DEFAULT_FORM_BY_BASE.get(base_key, "")
    preferred_form_token = form_token or default_form_token

    lookup_order: list[tuple[str, str, bool]] = [(base_key, preferred_form_token, is_shadow)]

    if preferred_form_token != form_token:
        lookup_order.append((base_key, form_token, is_shadow))

    if preferred_form_token:
        if is_shadow:
            lookup_order.append((base_key, preferred_form_token, False))
    else:
        if is_shadow:
            lookup_order.append((base_key, "", False))

    for key in lookup_order:
        match = _pick_best_species_id(species_ids_by_key.get(key, []), species_tags_by_id)
        if match is not None:
            return match

    if not form_token:
        match = _pick_best_species_id(
            species_ids_by_base_shadow.get((base_key, is_shadow), []),
            species_tags_by_id,
        )
        if match is not None:
            return match

    return None


def _resolve_species_move(
    move_name: str,
    lookup: dict[str, set[str]],
    legal_moves: set[str],
) -> tuple[str, str | None]:
    token = move_name.strip()
    if not token:
        return "", None

    candidates = set(lookup.get(token.upper(), set()))
    candidates.update(lookup.get(_canonical_move_key(token), set()))
    if not candidates:
        return "", f"unresolved_move:{token}"

    if legal_moves:
        legal_candidates = sorted(move_id for move_id in candidates if move_id in legal_moves)
        if len(legal_candidates) == 1:
            return legal_candidates[0], None
        if len(legal_candidates) > 1:
            return "", f"ambiguous_move:{token}->{','.join(legal_candidates)}"
        return "", f"unresolved_move:{token}"

    if len(candidates) == 1:
        return next(iter(candidates)), None

    fallback = sorted(candidates)
    return "", f"ambiguous_move:{token}->{','.join(fallback)}"


def _resolve_purified_return(move_name: str, lookup: dict[str, set[str]]) -> str:
    token = move_name.strip()
    if token.upper() != "RETURN":
        return ""
    candidates = set(lookup.get("RETURN", set()))
    candidates.update(lookup.get(_canonical_move_key("RETURN"), set()))
    if "RETURN" in candidates:
        return "RETURN"
    if len(candidates) == 1:
        return next(iter(candidates))
    return ""


def _parse_ivs(row: dict[str, str]) -> tuple[int, int, int] | None:
    try:
        atk = int(row["Atk IV"].strip())
        defense = int(row["Def IV"].strip())
        stamina = int(row["Sta IV"].strip())
    except (KeyError, ValueError):
        return None
    return atk, defense, stamina


def export_marked_g_to_pvpoke(
    input_csv: Path,
    output_file: Path,
    pokemon_path: Path,
    moves_path: Path,
    skip_report_path: Path | None = None,
) -> tuple[int, int, list[dict[str, str]]]:
    (
        species_ids_by_key,
        species_ids_by_base_shadow,
        legal_fast_by_species_id,
        legal_charged_by_species_id,
        species_tags_by_id,
    ) = _build_species_lookup(pokemon_path)
    move_lookup = _build_move_lookup(moves_path)

    output_lines: list[str] = []
    skipped = 0
    skipped_rows: list[dict[str, str]] = []

    with input_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("Marked for PvP use", "").strip() != "G":
                continue

            name = row.get("Name", "").strip()
            form = row.get("Form", "").strip()
            index = row.get("Index", "").strip()
            shadow = row.get("Shadow/Purified", "").strip()

            def add_skip(reason: str) -> None:
                nonlocal skipped
                skipped += 1
                skipped_rows.append(
                    {
                        "index": index,
                        "name": name,
                        "form": form,
                        "shadow_purified": shadow,
                        "reason": reason,
                    }
                )

            if not name:
                add_skip("missing_name")
                continue

            species_id = _resolve_species_id(
                name=name,
                form=form,
                shadow_purified=row.get("Shadow/Purified", ""),
                species_ids_by_key=species_ids_by_key,
                species_ids_by_base_shadow=species_ids_by_base_shadow,
                species_tags_by_id=species_tags_by_id,
            )
            if species_id is None:
                add_skip("unresolved_species")
                continue

            ivs = _parse_ivs(row)
            if ivs is None:
                add_skip("missing_or_invalid_ivs")
                continue

            level = _normalize_level(row.get("Level Max", "") or row.get("Level Min", ""))
            if not level:
                add_skip("missing_level")
                continue

            legal_fast = legal_fast_by_species_id.get(species_id, set())
            legal_charged = legal_charged_by_species_id.get(species_id, set())

            fast_move, fast_reason = _resolve_species_move(
                row.get("Quick Move", ""), move_lookup, legal_fast
            )
            charge_1, charge_1_reason = _resolve_species_move(
                row.get("Charge Move", ""), move_lookup, legal_charged
            )
            charge_2, charge_2_reason = _resolve_species_move(
                row.get("Charge Move 2", ""), move_lookup, legal_charged
            )

            fast_move_name = row.get("Quick Move", "").strip()
            charge_1_name = row.get("Charge Move", "").strip()
            charge_2_name = row.get("Charge Move 2", "").strip()

            if shadow == "2":
                if charge_1_name and not charge_1:
                    charge_1 = _resolve_purified_return(charge_1_name, move_lookup)
                    if charge_1:
                        charge_1_reason = None
                if charge_2_name and not charge_2:
                    charge_2 = _resolve_purified_return(charge_2_name, move_lookup)
                    if charge_2:
                        charge_2_reason = None

            if fast_move_name and not fast_move:
                reason = (
                    f"fast_{fast_reason}"
                    if fast_reason
                    else f"unresolved_fast_move:{fast_move_name}"
                )
                add_skip(reason)
                continue
            if charge_1_name and not charge_1:
                reason = (
                    f"charge1_{charge_1_reason}"
                    if charge_1_reason
                    else f"unresolved_charge_move_1:{charge_1_name}"
                )
                add_skip(reason)
                continue
            if charge_2_name and not charge_2:
                reason = (
                    f"charge2_{charge_2_reason}"
                    if charge_2_reason
                    else f"unresolved_charge_move_2:{charge_2_name}"
                )
                add_skip(reason)
                continue

            atk, defense, stamina = ivs
            output_lines.append(
                f"{species_id},{fast_move},{charge_1},{charge_2},{level},{atk},{defense},{stamina}"
            )

    output_file.write_text("\n".join(output_lines), encoding="utf-8")

    if skip_report_path is not None:
        with skip_report_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["index", "name", "form", "shadow_purified", "reason"],
            )
            writer.writeheader()
            writer.writerows(skipped_rows)

    return len(output_lines), skipped, skipped_rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Poke Genie CSV to PvPoke import lines for entries marked with G"
    )
    parser.add_argument("--input", default="poke_genie_export.csv", help="Path to Poke Genie CSV")
    parser.add_argument(
        "--output",
        default="poke_genie_g.pvpoke",
        help="Path to write PvPoke import lines",
    )
    parser.add_argument(
        "--pokemon-path",
        default="data/pokemon.json",
        help="Path to pokemon dataset used for speciesId resolution",
    )
    parser.add_argument(
        "--moves-path",
        default="data/moves.json",
        help="Path to moves dataset used for moveId resolution",
    )
    parser.add_argument(
        "--skip-report",
        default=None,
        help="Optional CSV path for skipped row diagnostics",
    )
    args = parser.parse_args()

    exported, skipped, skipped_rows = export_marked_g_to_pvpoke(
        input_csv=Path(args.input),
        output_file=Path(args.output),
        pokemon_path=Path(args.pokemon_path),
        moves_path=Path(args.moves_path),
        skip_report_path=Path(args.skip_report) if args.skip_report else None,
    )
    print(f"Exported {exported} rows to {args.output}")
    print(f"Skipped {skipped} marked rows due to missing/invalid data")
    if args.skip_report:
        print(f"Wrote skip diagnostics to {args.skip_report}")
    if skipped_rows:
        print("First skipped rows:")
        for row in skipped_rows[:5]:
            print(
                f"  - index={row['index']} name={row['name']} form={row['form']} "
                f"shadow={row['shadow_purified']} reason={row['reason']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
