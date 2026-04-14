import pytest

from pogo_team_optimizer.cli.main import build_parser, main


def test_build_parser_accepts_bfmaster_meta() -> None:
    parser = build_parser()

    args = parser.parse_args(["--meta", "bfmaster"])

    assert args.meta == "bfmaster"


def test_main_reports_missing_required_meta_files(tmp_path, monkeypatch) -> None:
    metas_config = tmp_path / "metas.json"
    pokemon_path = tmp_path / "pokemon.json"
    pokemon_path.write_text("[]", encoding="utf-8")
    metas_config.write_text(
        """
        {
          "metas": {
            "bfmaster": {
              "matrix_files": [
                "data/simulations/bfmaster_0-shield.csv",
                "data/simulations/bfmaster_1-shield.csv",
                "data/simulations/bfmaster_2-shield.csv"
              ],
              "required_files": ["data/bfmaster_points.csv"]
            }
          }
        }
        """.strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--meta",
            "bfmaster",
            "--metas-config",
            str(metas_config),
            "--pokemon-path",
            str(pokemon_path),
        ],
    )

    with pytest.raises(SystemExit, match="2"):
        main()
