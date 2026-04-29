import json

from pogo_team_optimizer.application.meta_config import (
    load_meta_config,
    validate_matrix_files,
    validate_required_files,
)


def test_load_meta_config_reads_matrix_files(tmp_path) -> None:
    path = tmp_path / "metas.json"
    path.write_text(
        json.dumps(
            {
                "metas": {
                    "great": {
                        "matrix_files": [
                            "data/simulations/great_0-shield.csv",
                            "data/simulations/great_1-shield.csv",
                            "data/simulations/great_2-shield.csv",
                        ]
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_meta_config(str(path), "great")
    assert config.name == "great"
    assert len(config.matrix_files) == 3
    assert config.switch_rankings_path is None
    assert config.required_files == ()


def test_load_meta_config_reads_optional_per_meta_fields(tmp_path) -> None:
    path = tmp_path / "metas.json"
    path.write_text(
        json.dumps(
            {
                "metas": {
                    "bfmaster": {
                        "matrix_files": [
                            "data/simulations/bfmaster_0-shield.csv",
                            "data/simulations/bfmaster_1-shield.csv",
                            "data/simulations/bfmaster_2-shield.csv",
                        ],
                        "switch_rankings_path": "data/rankings/cp10000_battlefrontiermaster_switches_rankings.csv",
                        "required_files": ["data/bfmaster_points.csv"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_meta_config(str(path), "bfmaster")

    assert (
        config.switch_rankings_path
        == "data/rankings/cp10000_battlefrontiermaster_switches_rankings.csv"
    )
    assert config.required_files == ("data/bfmaster_points.csv",)


def test_default_meta_config_includes_bayou_cup() -> None:
    config = load_meta_config("data/metas.json", "bayou")

    assert config.name == "bayou"
    assert config.matrix_files == (
        "data/simulations/bayou_0-shield.csv",
        "data/simulations/bayou_1-shield.csv",
        "data/simulations/bayou_2-shield.csv",
    )
    assert config.switch_rankings_path == "data/rankings/cp1500_bayou_switches_rankings.csv"
    assert validate_matrix_files(config.matrix_files) == []


def test_validate_matrix_files_reports_missing(tmp_path) -> None:
    existing = tmp_path / "exists.csv"
    existing.write_text("", encoding="utf-8")
    missing = validate_matrix_files((str(existing), str(tmp_path / "missing.csv")))
    assert len(missing) == 1


def test_validate_required_files_reports_missing(tmp_path) -> None:
    existing = tmp_path / "exists.csv"
    existing.write_text("", encoding="utf-8")

    missing = validate_required_files((str(existing), str(tmp_path / "missing.csv")))

    assert missing == [str(tmp_path / "missing.csv")]
