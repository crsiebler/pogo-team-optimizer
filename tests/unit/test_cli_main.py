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


def test_main_uses_meta_switch_rankings_when_no_cli_override(tmp_path, monkeypatch) -> None:
    matrix_paths = [tmp_path / f"bfmaster_{shield}-shield.csv" for shield in range(3)]
    for path in matrix_paths:
        path.write_text("", encoding="utf-8")

    rankings_path = tmp_path / "bfmaster_switches.csv"
    rankings_path.write_text("Pokemon,Score\nDialga,90\n", encoding="utf-8")
    points_path = tmp_path / "bfmaster_points.csv"
    points_path.write_text("species,points\nDialga,5\n", encoding="utf-8")

    metas_config = tmp_path / "metas.json"
    pokemon_path = tmp_path / "pokemon.json"
    pokemon_path.write_text("[]", encoding="utf-8")
    metas_config.write_text(
        f"""
        {{
          "metas": {{
            "bfmaster": {{
              "matrix_files": [
                "{matrix_paths[0]}",
                "{matrix_paths[1]}",
                "{matrix_paths[2]}"
              ],
              "switch_rankings_path": "{rankings_path}",
              "required_files": ["{points_path}"]
            }}
          }}
        }}
        """.strip(),
        encoding="utf-8",
    )

    captured: dict[str, object | None] = {"switch_rankings_path": None}

    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.CsvSimulationMatrixRepository",
        lambda files: object(),
    )
    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.PokemonJsonRepository",
        lambda path: object(),
    )

    def fake_switch_rankings_repository(path: str) -> object:
        captured["switch_rankings_path"] = path
        return object()

    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.CsvSwitchRankingsRepository",
        fake_switch_rankings_repository,
    )

    class FakeUseCase:
        def __init__(
            self,
            simulation_repo: object,
            pokemon_repo: object,
            switch_repo: object,
            battle_frontier_points_repo: object | None = None,
        ) -> None:
            captured["switch_repo"] = switch_repo

        def execute(self, **_: object) -> dict[str, object]:
            return {}

    monkeypatch.setattr("pogo_team_optimizer.cli.main.AnalyzeMetaUseCase", FakeUseCase)

    class FakeExporter:
        def export(self, result: dict[str, object], output_path: str | None = None) -> None:
            return None

    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.ExporterFactory.create",
        lambda *args, **kwargs: FakeExporter(),
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

    assert main() == 0
    assert captured["switch_rankings_path"] == str(rankings_path)


def test_main_uses_legacy_default_switch_rankings_for_other_metas(tmp_path, monkeypatch) -> None:
    matrix_paths = [tmp_path / f"great_{shield}-shield.csv" for shield in range(3)]
    for path in matrix_paths:
        path.write_text("", encoding="utf-8")

    default_rankings_path = tmp_path / "cp1500_all_switches_rankings.csv"
    default_rankings_path.write_text("Pokemon,Score\nLickilicky,92\n", encoding="utf-8")

    metas_config = tmp_path / "metas.json"
    pokemon_path = tmp_path / "pokemon.json"
    pokemon_path.write_text("[]", encoding="utf-8")
    metas_config.write_text(
        f"""
        {{
          "metas": {{
            "great": {{
              "matrix_files": [
                "{matrix_paths[0]}",
                "{matrix_paths[1]}",
                "{matrix_paths[2]}"
              ]
            }}
          }}
        }}
        """.strip(),
        encoding="utf-8",
    )

    captured: dict[str, object | None] = {"switch_rankings_path": None}

    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.CsvSimulationMatrixRepository",
        lambda files: object(),
    )
    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.PokemonJsonRepository",
        lambda path: object(),
    )

    def fake_switch_rankings_repository(path: str) -> object:
        captured["switch_rankings_path"] = path
        return object()

    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.CsvSwitchRankingsRepository",
        fake_switch_rankings_repository,
    )

    class FakeUseCase:
        def __init__(
            self,
            simulation_repo: object,
            pokemon_repo: object,
            switch_repo: object,
            battle_frontier_points_repo: object | None = None,
        ) -> None:
            captured["switch_repo"] = switch_repo

        def execute(self, **_: object) -> dict[str, object]:
            return {}

    monkeypatch.setattr("pogo_team_optimizer.cli.main.AnalyzeMetaUseCase", FakeUseCase)

    class FakeExporter:
        def export(self, result: dict[str, object], output_path: str | None = None) -> None:
            return None

    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.ExporterFactory.create",
        lambda *args, **kwargs: FakeExporter(),
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--meta",
            "great",
            "--metas-config",
            str(metas_config),
            "--pokemon-path",
            str(pokemon_path),
            "--switch-rankings-path",
            str(default_rankings_path),
        ],
    )

    assert main() == 0
    assert captured["switch_rankings_path"] == str(default_rankings_path)
