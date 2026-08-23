import json
from pathlib import Path

import pytest

from pogo_team_optimizer.application.meta_config import (
    load_meta_config,
    validate_matrix_files,
    validate_ranking_files,
    validate_required_files,
)
from pogo_team_optimizer.domain.models import RankingCategory


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
    assert config.ranking_paths == {}
    assert config.full_meta_ranking_paths == {}
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
                        "ranking_paths": {
                            "overall": "data/rankings/cp10000_battlefrontiermaster_overall_rankings.csv",
                            "switches": "data/rankings/cp10000_battlefrontiermaster_switches_rankings.csv",
                        },
                        "full_meta_ranking_paths": {
                            "overall": "data/rankings/cp10000_all_overall_rankings.csv"
                        },
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
    assert config.ranking_paths == {
        RankingCategory.OVERALL: "data/rankings/cp10000_battlefrontiermaster_overall_rankings.csv",
        RankingCategory.SWITCHES: "data/rankings/cp10000_battlefrontiermaster_switches_rankings.csv",
    }
    assert config.full_meta_ranking_paths == {
        RankingCategory.OVERALL: "data/rankings/cp10000_all_overall_rankings.csv",
    }
    assert config.required_files == ("data/bfmaster_points.csv",)


def test_load_meta_config_migrates_legacy_switch_rankings_path(tmp_path) -> None:
    path = tmp_path / "metas.json"
    path.write_text(
        json.dumps(
            {
                "metas": {
                    "great": {
                        "matrix_files": ["data/simulations/great_0-shield.csv"],
                        "switch_rankings_path": "data/rankings/cp1500_all_switches_rankings.csv",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_meta_config(str(path), "great")

    assert config.ranking_paths == {
        RankingCategory.SWITCHES: "data/rankings/cp1500_all_switches_rankings.csv",
    }
    assert config.switch_rankings_path == "data/rankings/cp1500_all_switches_rankings.csv"


def test_load_meta_config_rejects_unknown_ranking_category(tmp_path) -> None:
    path = tmp_path / "metas.json"
    path.write_text(
        json.dumps(
            {
                "metas": {
                    "great": {
                        "matrix_files": ["data/simulations/great_0-shield.csv"],
                        "ranking_paths": {"safe_switches": "data/rankings/safe.csv"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported ranking category 'safe_switches'"):
        load_meta_config(str(path), "great")


def test_load_meta_config_rejects_non_mapping_ranking_paths(tmp_path) -> None:
    path = tmp_path / "metas.json"
    path.write_text(
        json.dumps(
            {
                "metas": {
                    "great": {
                        "matrix_files": ["data/simulations/great_0-shield.csv"],
                        "ranking_paths": ["data/rankings/cp1500_all_overall_rankings.csv"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Meta 'great' must define object 'ranking_paths'"):
        load_meta_config(str(path), "great")


def test_load_meta_config_rejects_non_string_ranking_path_value(tmp_path) -> None:
    path = tmp_path / "metas.json"
    path.write_text(
        json.dumps(
            {
                "metas": {
                    "great": {
                        "matrix_files": ["data/simulations/great_0-shield.csv"],
                        "ranking_paths": {"overall": 123},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Meta 'great' ranking_paths.overall must be a string path",
    ):
        load_meta_config(str(path), "great")


@pytest.mark.parametrize(
    ("meta", "matrix_files", "ranking_prefix", "full_meta_prefix"),
    [
        (
            "bayou",
            (
                "data/simulations/bayou_0-shield.csv",
                "data/simulations/bayou_1-shield.csv",
                "data/simulations/bayou_2-shield.csv",
            ),
            "data/rankings/cp1500_bayou",
            "data/rankings/cp1500_all",
        ),
        (
            "naic",
            (
                "data/simulations/naic_0-shield.csv",
                "data/simulations/naic_1-shield.csv",
                "data/simulations/naic_2-shield.csv",
            ),
            "data/rankings/cp1500_naic2026",
            "data/rankings/cp1500_all",
        ),
        (
            "spellcraft",
            (
                "data/simulations/spellcraft_0-shield.csv",
                "data/simulations/spellcraft_1-shield.csv",
                "data/simulations/spellcraft_2-shield.csv",
            ),
            "data/rankings/cp1500_spellcraft",
            "data/rankings/cp1500_all",
        ),
    ],
)
def test_default_meta_config_includes_supported_cups(
    meta: str,
    matrix_files: tuple[str, ...],
    ranking_prefix: str,
    full_meta_prefix: str,
) -> None:
    config = load_meta_config("data/metas.json", meta)

    assert config.name == meta
    assert config.matrix_files == matrix_files
    assert config.switch_rankings_path == f"{ranking_prefix}_switches_rankings.csv"
    assert set(config.ranking_paths) == set(RankingCategory)
    assert set(config.full_meta_ranking_paths) == set(RankingCategory)
    assert config.ranking_paths[RankingCategory.OVERALL] == f"{ranking_prefix}_overall_rankings.csv"
    assert (
        config.full_meta_ranking_paths[RankingCategory.OVERALL]
        == f"{full_meta_prefix}_overall_rankings.csv"
    )


def test_default_meta_config_includes_master_rankings() -> None:
    config = load_meta_config("data/metas.json", "master")

    assert set(config.ranking_paths) == set(RankingCategory)
    assert set(config.full_meta_ranking_paths) == set(RankingCategory)
    assert (
        config.ranking_paths[RankingCategory.SWITCHES]
        == "data/rankings/cp10000_all_switches_rankings.csv"
    )


def test_default_configured_ranking_files_exist() -> None:
    metas = (
        "great",
        "majestic",
        "euic",
        "master",
        "bfretro",
        "bayou",
        "naic",
        "spellcraft",
        "bfmaster",
    )

    for meta in metas:
        config = load_meta_config("data/metas.json", meta)

        assert validate_ranking_files(config.ranking_paths, config.full_meta_ranking_paths) == []


def test_default_naic_matrix_files_exist() -> None:
    config = load_meta_config("data/metas.json", "naic")
    if any(not Path(path).exists() for path in config.matrix_files):
        pytest.skip("naic simulation matrices are optional local data fixtures")

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


def test_validate_ranking_files_reports_missing(tmp_path) -> None:
    existing = tmp_path / "exists.csv"
    existing.write_text("", encoding="utf-8")

    missing = validate_ranking_files(
        {RankingCategory.OVERALL: str(existing)},
        {RankingCategory.SWITCHES: str(tmp_path / "missing.csv")},
    )

    assert missing == [str(tmp_path / "missing.csv")]
