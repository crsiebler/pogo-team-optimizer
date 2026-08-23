from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.sync_pvpoke_data import (
    RANKING_CSV_HEADER,
    build_ranking_sync_target,
    collect_ranking_sync_targets,
    generate_ranking_csv_rows,
    parse_flat_ranking_filename,
    render_ranking_csv,
    sync_pvpoke_data,
)


def test_parse_flat_ranking_filename_preserves_cp_cup_and_category() -> None:
    assert parse_flat_ranking_filename("cp1500_bayou_overall_rankings.csv") == (
        1500,
        "bayou",
        "overall",
    )
    assert parse_flat_ranking_filename("cp10000_battlefrontiermaster_switches_rankings.csv") == (
        10000,
        "battlefrontiermaster",
        "switches",
    )


def test_build_ranking_sync_target_maps_flat_output_to_pvpoke_source(tmp_path: Path) -> None:
    target = build_ranking_sync_target(
        tmp_path,
        "data/rankings/cp1500_bayou_overall_rankings.csv",
        "overall",
    )

    assert target.cp == 1500
    assert target.cup == "bayou"
    assert target.category == "overall"
    assert target.source_path == (
        tmp_path / "vendor/pvpoke/src/data/rankings/bayou/overall/rankings-1500.json"
    )
    assert target.output_path == tmp_path / "data/rankings/cp1500_bayou_overall_rankings.csv"


def test_collect_ranking_sync_targets_deduplicates_meta_paths(tmp_path: Path) -> None:
    metas_path = tmp_path / "data/metas.json"
    _write_json(
        metas_path,
        {
            "metas": {
                "bayou": {
                    "matrix_files": [],
                    "ranking_paths": {"overall": "data/rankings/cp1500_bayou_overall_rankings.csv"},
                    "full_meta_ranking_paths": {
                        "overall": "data/rankings/cp1500_all_overall_rankings.csv"
                    },
                },
                "great": {
                    "matrix_files": [],
                    "ranking_paths": {"overall": "data/rankings/cp1500_all_overall_rankings.csv"},
                },
            }
        },
    )

    targets = collect_ranking_sync_targets(tmp_path, metas_path)

    assert [target.output_path.relative_to(tmp_path).as_posix() for target in targets] == [
        "data/rankings/cp1500_all_overall_rankings.csv",
        "data/rankings/cp1500_bayou_overall_rankings.csv",
    ]


def test_generate_ranking_csv_rows_matches_pvpoke_export_fields() -> None:
    rows = generate_ranking_csv_rows(
        rankings=[
            {
                "speciesId": "swampert",
                "speciesName": "Swampert",
                "score": 97.8,
                "moveset": ["MUD_SHOT", "HYDRO_CANNON", "EARTHQUAKE"],
                "stats": {"atk": 120.44, "def": 130.55, "hp": 140.2, "product": 1901},
            }
        ],
        pokemon_by_id={
            "swampert": {
                "speciesId": "swampert",
                "speciesName": "Swampert",
                "dex": 260,
                "types": ["water", "ground"],
                "defaultIVs": {"cp1500": [20.5, 1, 2, 3]},
                "buddyDistance": 3,
                "thirdMoveCost": 10000,
            }
        },
        moves_by_id={
            "MUD_SHOT": {"moveId": "MUD_SHOT", "name": "Mud Shot", "energyGain": 9},
            "HYDRO_CANNON": {"moveId": "HYDRO_CANNON", "name": "Hydro Cannon", "energy": 40},
            "EARTHQUAKE": {"moveId": "EARTHQUAKE", "name": "Earthquake", "energy": 65},
        },
        cp=1500,
    )

    csv_text = render_ranking_csv(rows)
    rendered_rows = list(csv.reader(csv_text.splitlines()))

    assert tuple(rendered_rows[0]) == RANKING_CSV_HEADER
    assert rendered_rows[1] == [
        "Swampert",
        "97.8",
        "260",
        "water",
        "ground",
        "120.4",
        "130.6",
        "140",
        "2204427",
        "20.5",
        "1629",
        "Mud Shot",
        "Hydro Cannon",
        "Earthquake",
        "5",
        "8",
        "3",
        "10000",
    ]


def test_sync_skips_missing_optional_rankings_and_keeps_existing_outputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_minimal_gamemaster(tmp_path)
    metas_path = _write_metas(tmp_path, "data/rankings/cp1500_missing_overall_rankings.csv")
    existing_output = tmp_path / "data/rankings/cp1500_missing_overall_rankings.csv"
    existing_output.parent.mkdir(parents=True, exist_ok=True)
    existing_output.write_text("existing\n", encoding="utf-8")

    written = sync_pvpoke_data(tmp_path, metas_path)

    assert written == ["data/pokemon.json", "data/moves.json"]
    assert existing_output.read_text(encoding="utf-8") == "existing\n"
    assert "warning: missing optional PvPoke ranking source" in capsys.readouterr().err


def test_sync_rejects_ranking_outputs_outside_data_rankings(tmp_path: Path) -> None:
    metas_path = _write_metas(tmp_path, "data/simulations/bayou_0-shield.csv")

    with pytest.raises(ValueError, match="must stay under data/rankings"):
        sync_pvpoke_data(tmp_path, metas_path)


def test_generate_ranking_csv_rows_handles_missing_stats_and_escapes_formula_text() -> None:
    rows = generate_ranking_csv_rows(
        rankings=[
            {
                "speciesId": "swampert",
                "speciesName": "=Swampert",
                "score": 97.8,
                "moveset": ["MUD_SHOT", "HYDRO_CANNON"],
            }
        ],
        pokemon_by_id={
            "swampert": {
                "speciesId": "swampert",
                "speciesName": "=Swampert",
                "dex": 260,
                "types": ["water", "ground"],
                "defaultIVs": {"cp1500": [20.5, 1, 2, 3]},
                "buddyDistance": 3,
                "thirdMoveCost": 10000,
            }
        },
        moves_by_id={
            "MUD_SHOT": {"moveId": "MUD_SHOT", "name": "+Mud Shot", "energyGain": 9},
            "HYDRO_CANNON": {"moveId": "HYDRO_CANNON", "name": "@Hydro Cannon", "energy": 40},
        },
        cp=1500,
    )

    rendered_rows = list(csv.reader(render_ranking_csv(rows).splitlines()))

    assert rendered_rows[1] == [
        "'=Swampert",
        "97.8",
        "260",
        "water",
        "ground",
        "",
        "",
        "",
        "",
        "20.5",
        "",
        "'+Mud Shot",
        "'@Hydro Cannon",
        "",
        "5",
        "0",
        "3",
        "10000",
    ]


def test_sync_fails_when_required_gamemaster_is_missing(tmp_path: Path) -> None:
    metas_path = _write_metas(tmp_path, "data/rankings/cp1500_bayou_overall_rankings.csv")

    with pytest.raises(ValueError, match="Missing required PvPoke pokemon gamemaster"):
        sync_pvpoke_data(tmp_path, metas_path)


def test_sync_writes_flat_rankings_and_never_simulations(tmp_path: Path) -> None:
    _write_minimal_gamemaster(tmp_path)
    metas_path = _write_metas(tmp_path, "data/rankings/cp1500_bayou_overall_rankings.csv")
    _write_json(
        tmp_path / "vendor/pvpoke/src/data/rankings/bayou/overall/rankings-1500.json",
        [
            {
                "speciesId": "swampert",
                "speciesName": "Swampert",
                "score": 97.8,
                "moveset": ["MUD_SHOT", "HYDRO_CANNON"],
                "stats": {"atk": 120.4, "def": 130.6, "hp": 140, "product": 2198800},
            }
        ],
    )

    first_written = sync_pvpoke_data(tmp_path, metas_path)
    output_path = tmp_path / "data/rankings/cp1500_bayou_overall_rankings.csv"
    first_csv = output_path.read_text(encoding="utf-8")
    second_written = sync_pvpoke_data(tmp_path, metas_path)

    assert first_written == second_written
    assert output_path.read_text(encoding="utf-8") == first_csv
    assert "data/rankings/cp1500_bayou_overall_rankings.csv" in first_written
    assert not (tmp_path / "data/simulations").exists()
    assert not any(path.startswith("data/simulations/") for path in first_written)


def _write_minimal_gamemaster(root: Path) -> None:
    _write_json(
        root / "vendor/pvpoke/src/data/gamemaster/pokemon.json",
        [
            {
                "speciesId": "swampert",
                "speciesName": "Swampert",
                "dex": 260,
                "types": ["water", "ground"],
                "defaultIVs": {"cp1500": [20.5, 1, 2, 3]},
                "buddyDistance": 3,
                "thirdMoveCost": 10000,
            }
        ],
    )
    _write_json(
        root / "vendor/pvpoke/src/data/gamemaster/moves.json",
        [
            {"moveId": "MUD_SHOT", "name": "Mud Shot", "energyGain": 9},
            {"moveId": "HYDRO_CANNON", "name": "Hydro Cannon", "energy": 40},
        ],
    )


def _write_metas(root: Path, ranking_path: str) -> Path:
    metas_path = root / "data/metas.json"
    _write_json(
        metas_path,
        {"metas": {"bayou": {"matrix_files": [], "ranking_paths": {"overall": ranking_path}}}},
    )
    return metas_path


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
