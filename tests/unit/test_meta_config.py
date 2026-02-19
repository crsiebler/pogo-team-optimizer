import json

from pogo_team_optimizer.application.meta_config import load_meta_config, validate_matrix_files


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


def test_validate_matrix_files_reports_missing(tmp_path) -> None:
    existing = tmp_path / "exists.csv"
    existing.write_text("", encoding="utf-8")
    missing = validate_matrix_files((str(existing), str(tmp_path / "missing.csv")))
    assert len(missing) == 1
