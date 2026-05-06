from __future__ import annotations

import json

import pytest

from pogo_team_optimizer.infrastructure.exporters.pvpoke_exporter import PvpokeExporter


def _write_json(path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_pvpoke_exporter_exports_species_and_move_ids(tmp_path) -> None:
    pokemon_path = tmp_path / "pokemon.json"
    moves_path = tmp_path / "moves.json"

    _write_json(
        pokemon_path,
        [
            {
                "speciesName": "Testmon",
                "speciesId": "testmon",
                "fastMoves": ["THUNDER_SHOCK"],
                "chargedMoves": ["WILD_CHARGE", "AURA_SPHERE"],
            }
        ],
    )
    _write_json(
        moves_path,
        [
            {"moveId": "THUNDER_SHOCK", "abbreviation": "TS", "name": "Thunder Shock"},
            {"moveId": "WILD_CHARGE", "abbreviation": "WC", "name": "Wild Charge"},
            {"moveId": "AURA_SPHERE", "abbreviation": "AuS", "name": "Aura Sphere"},
        ],
    )

    exporter = PvpokeExporter(str(pokemon_path), str(moves_path))
    result = {
        "recommended_team": {
            "members": [{"label": "Testmon TS+WC/AuS 1/1/1"}],
        }
    }

    rendered = exporter.export(result)
    assert rendered == "testmon,THUNDER_SHOCK,WILD_CHARGE,AURA_SPHERE,1,1,1"


def test_pvpoke_exporter_keeps_legacy_output_when_label_has_no_ivs(tmp_path) -> None:
    pokemon_path = tmp_path / "pokemon.json"
    moves_path = tmp_path / "moves.json"

    _write_json(
        pokemon_path,
        [
            {
                "speciesName": "Testmon",
                "speciesId": "testmon",
                "fastMoves": ["THUNDER_SHOCK"],
                "chargedMoves": ["WILD_CHARGE", "AURA_SPHERE"],
            }
        ],
    )
    _write_json(
        moves_path,
        [
            {"moveId": "THUNDER_SHOCK", "abbreviation": "TS", "name": "Thunder Shock"},
            {"moveId": "WILD_CHARGE", "abbreviation": "WC", "name": "Wild Charge"},
            {"moveId": "AURA_SPHERE", "abbreviation": "AuS", "name": "Aura Sphere"},
        ],
    )

    exporter = PvpokeExporter(str(pokemon_path), str(moves_path))
    result = {
        "recommended_team": {
            "members": [{"label": "Testmon TS+WC/AuS"}],
        }
    }

    rendered = exporter.export(result)
    assert rendered == "testmon,THUNDER_SHOCK,WILD_CHARGE,AURA_SPHERE"


def test_pvpoke_exporter_uses_fallback_alias_without_abbreviation(tmp_path) -> None:
    pokemon_path = tmp_path / "pokemon.json"
    moves_path = tmp_path / "moves.json"

    _write_json(
        pokemon_path,
        [
            {
                "speciesName": "Testmon",
                "speciesId": "testmon",
                "fastMoves": ["THUNDER_SHOCK"],
                "chargedMoves": ["MYSTIC_BURST", "WILD_CHARGE"],
            }
        ],
    )
    _write_json(
        moves_path,
        [
            {"moveId": "THUNDER_SHOCK", "abbreviation": "TS", "name": "Thunder Shock"},
            {"moveId": "MYSTIC_BURST", "name": "Mystic Burst"},
            {"moveId": "WILD_CHARGE", "abbreviation": "WC", "name": "Wild Charge"},
        ],
    )

    exporter = PvpokeExporter(str(pokemon_path), str(moves_path))
    result = {
        "recommended_team": {
            "members": [{"label": "Testmon TS+MB/WC 1/1/1"}],
        }
    }

    rendered = exporter.export(result)
    assert rendered == "testmon,THUNDER_SHOCK,MYSTIC_BURST,WILD_CHARGE,1,1,1"


def test_pvpoke_exporter_fails_on_unresolved_move(tmp_path) -> None:
    pokemon_path = tmp_path / "pokemon.json"
    moves_path = tmp_path / "moves.json"

    _write_json(
        pokemon_path,
        [
            {
                "speciesName": "Testmon",
                "speciesId": "testmon",
                "fastMoves": ["THUNDER_SHOCK"],
                "chargedMoves": ["WILD_CHARGE", "AURA_SPHERE"],
            }
        ],
    )
    _write_json(
        moves_path,
        [
            {"moveId": "THUNDER_SHOCK", "abbreviation": "TS", "name": "Thunder Shock"},
            {"moveId": "WILD_CHARGE", "abbreviation": "WC", "name": "Wild Charge"},
            {"moveId": "AURA_SPHERE", "abbreviation": "AuS", "name": "Aura Sphere"},
        ],
    )

    exporter = PvpokeExporter(str(pokemon_path), str(moves_path))
    result = {
        "recommended_team": {
            "members": [{"label": "Testmon TS+XX/AuS 1/1/1"}],
        }
    }

    with pytest.raises(ValueError, match="Unresolved move token"):
        exporter.export(result)


def test_pvpoke_exporter_resolves_form_and_shadow_species_ids(tmp_path) -> None:
    pokemon_path = tmp_path / "pokemon.json"
    moves_path = tmp_path / "moves.json"

    _write_json(
        pokemon_path,
        [
            {
                "speciesName": "Ninetales (Alolan)",
                "speciesId": "ninetales_alolan",
                "fastMoves": ["POWDER_SNOW"],
                "chargedMoves": ["WEATHER_BALL_ICE", "CHARM"],
            },
            {
                "speciesName": "Ninetales (Alolan) (Shadow)",
                "speciesId": "ninetales_alolan_shadow",
                "fastMoves": ["POWDER_SNOW"],
                "chargedMoves": ["WEATHER_BALL_ICE", "CHARM"],
            },
            {
                "speciesName": "Annihilape (Shadow)",
                "speciesId": "annihilape_shadow",
                "fastMoves": ["COUNTER"],
                "chargedMoves": ["RAGE_FIST", "CLOSE_COMBAT"],
            },
        ],
    )
    _write_json(
        moves_path,
        [
            {"moveId": "POWDER_SNOW", "abbreviation": "PS", "name": "Powder Snow"},
            {"moveId": "WEATHER_BALL_ICE", "abbreviation": "WBI", "name": "Weather Ball Ice"},
            {"moveId": "CHARM", "abbreviation": "Ch", "name": "Charm"},
            {"moveId": "COUNTER", "abbreviation": "C", "name": "Counter"},
            {"moveId": "RAGE_FIST", "abbreviation": "RF", "name": "Rage Fist"},
            {"moveId": "CLOSE_COMBAT", "abbreviation": "CC", "name": "Close Combat"},
        ],
    )

    exporter = PvpokeExporter(str(pokemon_path), str(moves_path))
    result = {
        "recommended_team": {
            "members": [
                {"label": "Ninetales (Alolan) PS+WBI/Ch 1/1/1"},
                {"label": "Ninetales (Alolan) (Shadow) PS+WBI/Ch 1/1/1"},
                {"label": "Annihilape (Shadow) C+RF/CC 1/1/1"},
            ],
        }
    }

    rendered = exporter.export(result)
    assert rendered.splitlines()[0].startswith("ninetales_alolan,")
    assert rendered.splitlines()[1].startswith("ninetales_alolan_shadow,")
    assert rendered.splitlines()[2].startswith("annihilape_shadow,")


def test_pvpoke_exporter_avoids_duplicate_species_name_shadow_alias(tmp_path) -> None:
    pokemon_path = tmp_path / "pokemon.json"
    moves_path = tmp_path / "moves.json"

    _write_json(
        pokemon_path,
        [
            {
                "speciesName": "Golisopod",
                "speciesId": "golisopod",
                "fastMoves": ["SHADOW_CLAW"],
                "chargedMoves": ["X_SCISSOR", "AQUA_JET"],
            },
            {
                "speciesName": "Golisopod",
                "speciesId": "golisopodsh",
                "tags": ["duplicate", "duplicate1500"],
                "fastMoves": ["SHADOW_CLAW"],
                "chargedMoves": ["X_SCISSOR", "AQUA_JET"],
            },
        ],
    )
    _write_json(
        moves_path,
        [
            {"moveId": "SHADOW_CLAW", "abbreviation": "SC", "name": "Shadow Claw"},
            {"moveId": "X_SCISSOR", "abbreviation": "XS", "name": "X-Scissor"},
            {"moveId": "AQUA_JET", "abbreviation": "AJ", "name": "Aqua Jet"},
        ],
    )

    exporter = PvpokeExporter(str(pokemon_path), str(moves_path))
    result = {
        "recommended_team": {
            "members": [{"label": "Golisopod SC+XS/AJ 1/1/1"}],
        }
    }
    rendered = exporter.export(result)
    assert rendered == "golisopod,SHADOW_CLAW,X_SCISSOR,AQUA_JET,1,1,1"
