from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


RANKING_CSV_HEADER = (
    "Pokemon",
    "Score",
    "Dex",
    "Type 1",
    "Type 2",
    "Attack",
    "Defense",
    "Stamina",
    "Stat Product",
    "Level",
    "CP",
    "Fast Move",
    "Charged Move 1",
    "Charged Move 2",
    "Charged Move 1 Count",
    "Charged Move 2 Count",
    "Buddy Distance",
    "Charged Move Cost",
)
SUPPORTED_RANKING_CATEGORIES = frozenset(
    {"overall", "leads", "switches", "closers", "attackers", "chargers", "consistency"}
)
RANKING_FILENAME_PREFIX = "cp"
RANKING_FILENAME_SUFFIX = "_rankings.csv"


@dataclass(frozen=True)
class RankingSyncTarget:
    cp: int
    cup: str
    category: str
    source_path: Path
    output_path: Path


def collect_ranking_sync_targets(root: Path, metas_path: Path) -> tuple[RankingSyncTarget, ...]:
    metas_data = _load_json(metas_path)
    metas = metas_data.get("metas")
    if not isinstance(metas, dict):
        raise ValueError(f"{metas_path} must contain a 'metas' object")

    targets_by_output: dict[Path, RankingSyncTarget] = {}
    for meta_value in metas.values():
        if not isinstance(meta_value, dict):
            continue
        for field_name in ("ranking_paths", "full_meta_ranking_paths"):
            ranking_paths = meta_value.get(field_name, {})
            if not isinstance(ranking_paths, dict):
                continue
            for category, output_path_text in ranking_paths.items():
                if not isinstance(category, str) or not isinstance(output_path_text, str):
                    continue
                target = build_ranking_sync_target(root, output_path_text, category)
                targets_by_output.setdefault(target.output_path, target)
    return tuple(sorted(targets_by_output.values(), key=lambda target: target.output_path.as_posix()))


def build_ranking_sync_target(root: Path, output_path_text: str, category: str | None = None) -> RankingSyncTarget:
    output_path = _validated_ranking_output_path(root, output_path_text)
    cp, cup, filename_category = parse_flat_ranking_filename(output_path.name)
    if category is not None and category != filename_category:
        raise ValueError(
            f"Ranking path category mismatch for {output_path_text}: "
            f"config has {category!r}, filename has {filename_category!r}"
        )

    source_path = (
        root
        / "vendor"
        / "pvpoke"
        / "src"
        / "data"
        / "rankings"
        / cup
        / filename_category
        / f"rankings-{cp}.json"
    )
    return RankingSyncTarget(
        cp=cp,
        cup=cup,
        category=filename_category,
        source_path=source_path,
        output_path=output_path,
    )


def parse_flat_ranking_filename(filename: str) -> tuple[int, str, str]:
    if not filename.startswith(RANKING_FILENAME_PREFIX) or not filename.endswith(
        RANKING_FILENAME_SUFFIX
    ):
        raise ValueError(
            f"Ranking filename must match cp{{cp}}_{{cup}}_{{category}}_rankings.csv: {filename}"
        )

    stem = filename[: -len(RANKING_FILENAME_SUFFIX)]
    cp_text, remainder = stem.split("_", 1)
    try:
        cp = int(cp_text.removeprefix(RANKING_FILENAME_PREFIX))
    except ValueError as error:
        raise ValueError(f"Ranking filename has invalid CP value: {filename}") from error

    for category in sorted(SUPPORTED_RANKING_CATEGORIES, key=len, reverse=True):
        suffix = f"_{category}"
        if remainder.endswith(suffix):
            cup = remainder[: -len(suffix)]
            if not cup:
                raise ValueError(f"Ranking filename has empty cup value: {filename}")
            return cp, cup, category
    supported = ", ".join(sorted(SUPPORTED_RANKING_CATEGORIES))
    raise ValueError(f"Ranking filename has unsupported category: {filename}. Expected: {supported}")


def sync_pvpoke_data(root: Path, metas_path: Path | None = None) -> list[str]:
    metas_path = metas_path or root / "data" / "metas.json"
    targets = collect_ranking_sync_targets(root, metas_path)
    vendor_gamemaster = root / "vendor" / "pvpoke" / "src" / "data" / "gamemaster"
    source_pokemon_path = vendor_gamemaster / "pokemon.json"
    source_moves_path = vendor_gamemaster / "moves.json"
    _require_file(source_pokemon_path, "PvPoke pokemon gamemaster")
    _require_file(source_moves_path, "PvPoke moves gamemaster")

    pokemon_data = _load_json(source_pokemon_path)
    moves_data = _load_json(source_moves_path)
    if not isinstance(pokemon_data, list):
        raise ValueError(f"{source_pokemon_path} must contain a JSON array")
    if not isinstance(moves_data, list):
        raise ValueError(f"{source_moves_path} must contain a JSON array")

    written: list[str] = []
    _copy_json(source_pokemon_path, root / "data" / "pokemon.json")
    written.append("data/pokemon.json")
    _copy_json(source_moves_path, root / "data" / "moves.json")
    written.append("data/moves.json")

    pokemon_by_id = _index_by_id(pokemon_data, "speciesId")
    moves_by_id = _index_by_id(moves_data, "moveId")
    for target in targets:
        if not target.source_path.exists():
            print(f"warning: missing optional PvPoke ranking source {target.source_path}", file=sys.stderr)
            continue
        rows = generate_ranking_csv_rows(
            rankings=_load_ranking_rows(target.source_path),
            pokemon_by_id=pokemon_by_id,
            moves_by_id=moves_by_id,
            cp=target.cp,
        )
        csv_text = render_ranking_csv(rows)
        validate_ranking_csv(csv_text, target.output_path)
        _write_text_atomic(target.output_path, csv_text)
        written.append(target.output_path.relative_to(root).as_posix())

    invalid_outputs = [path for path in written if path.startswith("data/simulations/")]
    if invalid_outputs:
        raise RuntimeError(f"PvPoke sync must not write simulation matrices: {invalid_outputs}")
    return written


def generate_ranking_csv_rows(
    rankings: Sequence[Mapping[str, Any]],
    pokemon_by_id: Mapping[str, Mapping[str, Any]],
    moves_by_id: Mapping[str, Mapping[str, Any]],
    cp: int,
) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for ranking in rankings:
        species_id = _required_str(ranking, "speciesId")
        pokemon = pokemon_by_id.get(species_id)
        if pokemon is None:
            raise ValueError(f"Ranking references unknown speciesId {species_id!r}")

        moveset = ranking.get("moveset")
        if not isinstance(moveset, list) or len(moveset) < 2:
            raise ValueError(f"Ranking for {species_id!r} must contain a fast and charged moveset")
        fast_move = _lookup_move(moves_by_id, moveset[0])
        charged_move_1 = _lookup_move(moves_by_id, moveset[1])
        charged_move_2 = _lookup_move(moves_by_id, moveset[2]) if len(moveset) > 2 else None

        stats = ranking.get("stats")
        if isinstance(stats, dict):
            atk = _optional_number(stats, "atk")
            defense = _optional_number(stats, "def")
            hp = _optional_number(stats, "hp")
        else:
            atk = None
            defense = None
            hp = None
        level = _default_level(pokemon, cp)
        charged_move_1_count = _charged_move_count(fast_move, charged_move_1)
        charged_move_2_count = _charged_move_count(fast_move, charged_move_2)

        rows.append(
            (
                _sanitize_csv_text(str(ranking.get("speciesName") or pokemon.get("speciesName") or species_id)),
                _format_value(ranking.get("score")),
                _format_value(pokemon.get("dex")),
                _sanitize_csv_text(_pokemon_type(pokemon, 0)),
                _sanitize_csv_text(_pokemon_type(pokemon, 1)),
                _format_optional_decimal(atk, 1),
                _format_optional_decimal(defense, 1),
                _format_optional_integer(hp),
                _format_optional_integer(_stat_product(atk, defense, hp)),
                _format_value(level),
                _format_value(_estimated_cp(atk, defense, hp)),
                _sanitize_csv_text(_move_name(fast_move)),
                _sanitize_csv_text(_move_name(charged_move_1)),
                _sanitize_csv_text(_move_name(charged_move_2)) if charged_move_2 is not None else "",
                str(charged_move_1_count),
                str(charged_move_2_count),
                _format_value(pokemon.get("buddyDistance", "")),
                _format_value(pokemon.get("thirdMoveCost", "")),
            )
        )
    return rows


def render_ranking_csv(rows: Iterable[Sequence[str]]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(RANKING_CSV_HEADER)
    writer.writerows(rows)
    return buffer.getvalue()


def validate_ranking_csv(csv_text: str, output_path: Path) -> None:
    reader = csv.reader(csv_text.splitlines())
    try:
        header = tuple(next(reader))
    except StopIteration as error:
        raise ValueError(f"Generated ranking CSV is empty for {output_path}") from error
    if header != RANKING_CSV_HEADER:
        raise ValueError(f"Generated ranking CSV header mismatch for {output_path}")
    for line_number, row in enumerate(reader, start=2):
        if len(row) != len(RANKING_CSV_HEADER):
            raise ValueError(
                f"Generated ranking CSV row {line_number} for {output_path} has "
                f"{len(row)} fields; expected {len(RANKING_CSV_HEADER)}"
            )
        if not row[0] or not row[1]:
            raise ValueError(f"Generated ranking CSV row {line_number} missing Pokemon or Score")


def _load_ranking_rows(path: Path) -> list[Mapping[str, Any]]:
    rankings = _load_json(path)
    if not isinstance(rankings, list):
        raise ValueError(f"{path} must contain a JSON array")
    return [_require_mapping(row, f"{path} ranking row") for row in rankings]


def _validated_ranking_output_path(root: Path, output_path_text: str) -> Path:
    output_path = Path(output_path_text)
    if output_path.is_absolute():
        raise ValueError(f"Ranking output path must be relative: {output_path_text}")
    resolved_root = root.resolve()
    resolved_output = (resolved_root / output_path).resolve()
    rankings_dir = (resolved_root / "data" / "rankings").resolve()
    try:
        resolved_output.relative_to(rankings_dir)
    except ValueError as error:
        raise ValueError(
            f"Ranking output path must stay under data/rankings: {output_path_text}"
        ) from error
    return resolved_output


def _copy_json(source_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(f".{output_path.name}.tmp")
    shutil.copyfile(source_path, temp_path)
    temp_path.replace(output_path)


def _write_text_atomic(output_path: Path, text: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(f".{output_path.name}.tmp")
    temp_path.write_text(text, encoding="utf-8", newline="")
    temp_path.replace(output_path)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _require_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise ValueError(f"Missing required {description}: {path}")


def _index_by_id(rows: Sequence[Any], id_field: str) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        mapping = _require_mapping(row, f"{id_field} row")
        id_value = mapping.get(id_field)
        if isinstance(id_value, str):
            indexed[id_value] = mapping
    return indexed


def _require_mapping(value: Any, description: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be an object")
    return value


def _required_str(mapping: Mapping[str, Any], field: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Expected non-empty string field {field!r}")
    return value


def _lookup_move(moves_by_id: Mapping[str, Mapping[str, Any]], move_id: Any) -> Mapping[str, Any]:
    if not isinstance(move_id, str):
        raise ValueError(f"Move id must be a string: {move_id!r}")
    move = moves_by_id.get(move_id)
    if move is None:
        raise ValueError(f"Ranking references unknown moveId {move_id!r}")
    return move


def _number(mapping: Mapping[str, Any], field: str, default: float | None = None) -> float:
    value = mapping.get(field, default)
    if not isinstance(value, int | float):
        raise ValueError(f"Expected numeric field {field!r}")
    return float(value)


def _optional_number(mapping: Mapping[str, Any], field: str) -> float | None:
    value = mapping.get(field)
    if value is None:
        return None
    if not isinstance(value, int | float):
        raise ValueError(f"Expected numeric field {field!r}")
    return float(value)


def _default_level(pokemon: Mapping[str, Any], cp: int) -> int | float | str:
    default_ivs = pokemon.get("defaultIVs")
    if not isinstance(default_ivs, dict):
        return ""
    cp_ivs = default_ivs.get(f"cp{cp}")
    if not isinstance(cp_ivs, list) or not cp_ivs:
        return ""
    level = cp_ivs[0]
    if isinstance(level, int | float):
        return level
    return ""


def _charged_move_count(
    fast_move: Mapping[str, Any], charged_move: Mapping[str, Any] | None
) -> int:
    if charged_move is None:
        return 0
    energy_gain = _number(fast_move, "energyGain")
    energy = _number(charged_move, "energy")
    if energy_gain <= 0:
        return 0
    return math.ceil(energy / energy_gain)


def _stat_product(atk: float | None, defense: float | None, hp: float | None) -> float | None:
    if atk is None or defense is None or hp is None:
        return None
    return atk * defense * hp


def _estimated_cp(atk: float | None, defense: float | None, hp: float | None) -> int | str:
    if atk is None or defense is None or hp is None:
        return ""
    return max(10, math.floor(atk * math.sqrt(defense) * math.sqrt(hp) / 10))


def _move_name(move: Mapping[str, Any]) -> str:
    return str(move.get("name") or move.get("moveId") or "")


def _pokemon_type(pokemon: Mapping[str, Any], index: int) -> str:
    types = pokemon.get("types")
    if isinstance(types, list) and index < len(types) and isinstance(types[index], str):
        return types[index]
    return "none"


def _format_decimal(value: float, places: int) -> str:
    rounded = round(value, places)
    return f"{rounded:.{places}f}"


def _format_optional_decimal(value: float | None, places: int) -> str:
    if value is None:
        return ""
    return _format_decimal(value, places)


def _format_optional_integer(value: float | None) -> str:
    if value is None:
        return ""
    return str(round(value))


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _sanitize_csv_text(value: str) -> str:
    if value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync local PvPoke gamemaster and ranking CSV data")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument(
        "--metas-path",
        type=Path,
        default=None,
        help="metas config path; defaults to data/metas.json under --root",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    metas_path = args.metas_path.resolve() if args.metas_path is not None else None
    try:
        written = sync_pvpoke_data(root, metas_path)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for path in written:
        print(f"synced {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
