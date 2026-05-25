from pathlib import Path

import pytest

from pogo_team_optimizer.cli.main import build_parser, main


@pytest.mark.parametrize("meta", ["bfmaster", "bayou", "naic", "spellcraft"])
def test_build_parser_accepts_supported_metas(meta: str) -> None:
    parser = build_parser()

    args = parser.parse_args(["--meta", meta])

    assert args.meta == meta


def test_build_parser_rejects_unsupported_crucible_meta() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit, match="2"):
        parser.parse_args(["--meta", "crucible"])


def test_build_parser_defaults_to_five_top_lineups() -> None:
    parser = build_parser()

    args = parser.parse_args([])

    assert args.top_lineups == 5


def test_build_parser_defaults_to_one_worker() -> None:
    parser = build_parser()

    args = parser.parse_args([])

    assert args.workers == 1


def test_main_rejects_more_than_ten_top_lineups(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["prog", "--top-lineups", "11"])

    with pytest.raises(SystemExit, match="2"):
        main()


def test_main_rejects_negative_top_lineups(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["prog", "--top-lineups", "-1"])

    with pytest.raises(SystemExit, match="2"):
        main()


def test_main_rejects_zero_workers(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["prog", "--workers", "0"])

    with pytest.raises(SystemExit, match="2"):
        main()


def test_main_rejects_too_many_workers(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["prog", "--workers", "33"])

    with pytest.raises(SystemExit, match="2"):
        main()


def test_main_rejects_deprecated_output_argument(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["prog", "--output", "analysis.json"])

    with pytest.raises(SystemExit, match="2"):
        main()


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
    moves_path = tmp_path / "moves.json"
    type_effectiveness_path = tmp_path / "type-effectiveness.json"
    pokemon_path.write_text("[]", encoding="utf-8")
    moves_path.write_text("[]", encoding="utf-8")
    type_effectiveness_path.write_text("{}", encoding="utf-8")
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
              "ranking_paths": {{
                "switches": "{rankings_path}"
              }},
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
            move_repo: object | None = None,
            type_effectiveness_repo: object | None = None,
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
            "--moves-path",
            str(moves_path),
            "--type-effectiveness-path",
            str(type_effectiveness_path),
            "--output-dir",
            str(tmp_path / "output"),
        ],
    )

    assert main() == 0
    assert captured["switch_rankings_path"] == str(rankings_path)


def test_main_reports_missing_configured_ranking_files_before_repositories(
    tmp_path,
    monkeypatch,
) -> None:
    matrix_paths = [tmp_path / f"great_{shield}-shield.csv" for shield in range(3)]
    for path in matrix_paths:
        path.write_text("", encoding="utf-8")

    metas_config = tmp_path / "metas.json"
    pokemon_path = tmp_path / "pokemon.json"
    moves_path = tmp_path / "moves.json"
    type_effectiveness_path = tmp_path / "type-effectiveness.json"
    pokemon_path.write_text("[]", encoding="utf-8")
    moves_path.write_text("[]", encoding="utf-8")
    type_effectiveness_path.write_text("{}", encoding="utf-8")
    missing_rankings_path = tmp_path / "missing_overall.csv"
    metas_config.write_text(
        f"""
        {{
          "metas": {{
            "great": {{
              "matrix_files": [
                "{matrix_paths[0]}",
                "{matrix_paths[1]}",
                "{matrix_paths[2]}"
              ],
              "ranking_paths": {{
                "overall": "{missing_rankings_path}"
              }}
            }}
          }}
        }}
        """.strip(),
        encoding="utf-8",
    )

    def fail_repository_construction(*_: object) -> object:
        raise AssertionError("repositories should not be constructed")

    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.CsvSimulationMatrixRepository",
        fail_repository_construction,
    )
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
            "--moves-path",
            str(moves_path),
            "--type-effectiveness-path",
            str(type_effectiveness_path),
        ],
    )

    with pytest.raises(SystemExit, match="2"):
        main()


def test_main_switch_override_replaces_stale_configured_switch_path(tmp_path, monkeypatch) -> None:
    matrix_paths = [tmp_path / f"great_{shield}-shield.csv" for shield in range(3)]
    for path in matrix_paths:
        path.write_text("", encoding="utf-8")

    valid_overall_path = tmp_path / "overall.csv"
    valid_override_path = tmp_path / "override_switches.csv"
    valid_overall_path.write_text("Pokemon,Score\nLickilicky,93\n", encoding="utf-8")
    valid_override_path.write_text("Pokemon,Score\nLickilicky,92\n", encoding="utf-8")

    metas_config = tmp_path / "metas.json"
    pokemon_path = tmp_path / "pokemon.json"
    moves_path = tmp_path / "moves.json"
    type_effectiveness_path = tmp_path / "type-effectiveness.json"
    pokemon_path.write_text("[]", encoding="utf-8")
    moves_path.write_text("[]", encoding="utf-8")
    type_effectiveness_path.write_text("{}", encoding="utf-8")
    metas_config.write_text(
        f"""
        {{
          "metas": {{
            "great": {{
              "matrix_files": [
                "{matrix_paths[0]}",
                "{matrix_paths[1]}",
                "{matrix_paths[2]}"
              ],
              "ranking_paths": {{
                "overall": "{valid_overall_path}",
                "switches": "{tmp_path / 'missing_switches.csv'}"
              }}
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
        def __init__(self, *_: object) -> None:
            pass

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
            "great",
            "--metas-config",
            str(metas_config),
            "--pokemon-path",
            str(pokemon_path),
            "--moves-path",
            str(moves_path),
            "--type-effectiveness-path",
            str(type_effectiveness_path),
            "--switch-rankings-path",
            str(valid_override_path),
            "--output-dir",
            str(tmp_path / "output"),
        ],
    )

    assert main() == 0
    assert captured["switch_rankings_path"] == str(valid_override_path)


def test_main_uses_legacy_default_switch_rankings_for_other_metas(tmp_path, monkeypatch) -> None:
    matrix_paths = [tmp_path / f"great_{shield}-shield.csv" for shield in range(3)]
    for path in matrix_paths:
        path.write_text("", encoding="utf-8")

    default_rankings_path = tmp_path / "cp1500_all_switches_rankings.csv"
    default_rankings_path.write_text("Pokemon,Score\nLickilicky,92\n", encoding="utf-8")

    metas_config = tmp_path / "metas.json"
    pokemon_path = tmp_path / "pokemon.json"
    moves_path = tmp_path / "moves.json"
    type_effectiveness_path = tmp_path / "type-effectiveness.json"
    pokemon_path.write_text("[]", encoding="utf-8")
    moves_path.write_text("[]", encoding="utf-8")
    type_effectiveness_path.write_text("{}", encoding="utf-8")
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
            move_repo: object | None = None,
            type_effectiveness_repo: object | None = None,
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
            "--moves-path",
            str(moves_path),
            "--type-effectiveness-path",
            str(type_effectiveness_path),
            "--switch-rankings-path",
            str(default_rankings_path),
            "--output-dir",
            str(tmp_path / "output"),
        ],
    )

    assert main() == 0
    assert captured["switch_rankings_path"] == str(default_rankings_path)


def test_main_exports_all_formats_from_one_analysis_result(tmp_path, monkeypatch, capsys) -> None:
    matrix_paths = [tmp_path / f"bayou_{shield}-shield.csv" for shield in range(3)]
    for path in matrix_paths:
        path.write_text("", encoding="utf-8")

    metas_config = tmp_path / "metas.json"
    pokemon_path = tmp_path / "pokemon.json"
    moves_path = tmp_path / "moves.json"
    output_dir = tmp_path / "output"
    pokemon_path.write_text("[]", encoding="utf-8")
    moves_path.write_text("[]", encoding="utf-8")
    metas_config.write_text(
        f"""
        {{
          "metas": {{
            "bayou": {{
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

    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.CsvSimulationMatrixRepository",
        lambda files: object(),
    )
    monkeypatch.setattr(
        "pogo_team_optimizer.cli.main.PokemonJsonRepository",
        lambda path: object(),
    )

    execute_calls = 0
    execute_kwargs: dict[str, object] = {}
    result = {"recommended_team": {"members": [], "metrics": {}}, "coverage": [], "safe_cores": [], "threats": []}

    class FakeUseCase:
        def __init__(self, *_: object) -> None:
            pass

        def execute(self, **kwargs: object) -> dict[str, object]:
            nonlocal execute_calls
            execute_calls += 1
            execute_kwargs.update(kwargs)
            return result

    monkeypatch.setattr("pogo_team_optimizer.cli.main.AnalyzeMetaUseCase", FakeUseCase)

    exports: list[tuple[str, str | None, int]] = []

    class FakeExporter:
        def __init__(self, output_format: str) -> None:
            self.output_format = output_format

        def export(self, exported_result: dict[str, object], output_path: str | None = None) -> str | None:
            exports.append((self.output_format, output_path, id(exported_result)))
            if output_path is not None:
                Path(output_path).write_text(self.output_format, encoding="utf-8")
                return None
            return "text report"

    def fake_create(output_format: str, **_: object) -> FakeExporter:
        return FakeExporter(output_format)

    monkeypatch.setattr("pogo_team_optimizer.cli.main.ExporterFactory.create", fake_create)
    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--meta",
            "bayou",
            "--metas-config",
            str(metas_config),
            "--pokemon-path",
            str(pokemon_path),
            "--moves-path",
            str(moves_path),
            "--output-dir",
            str(output_dir),
            "--top-lineups",
            "10",
            "--workers",
            "2",
        ],
    )

    assert main() == 0

    assert execute_calls == 1
    assert execute_kwargs["top_lineups"] == 10
    assert execute_kwargs["workers"] == 2
    assert capsys.readouterr().out == "text report\n"
    assert exports == [
        ("text", None, id(result)),
        ("markdown", str(output_dir / "bayou.md"), id(result)),
        ("json", str(output_dir / "bayou.json"), id(result)),
        ("csv", str(output_dir / "bayou.csv"), id(result)),
        ("excel", str(output_dir / "bayou.xlsx"), id(result)),
        ("pvpoke", str(output_dir / "bayou.pvpoke"), id(result)),
    ]
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "bayou.csv",
        "bayou.json",
        "bayou.md",
        "bayou.pvpoke",
        "bayou.txt",
        "bayou.xlsx",
    ]
