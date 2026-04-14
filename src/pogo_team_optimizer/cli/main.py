from __future__ import annotations

import argparse
from pathlib import Path

from pogo_team_optimizer.application.meta_config import (
    load_meta_config,
    validate_matrix_files,
    validate_required_files,
)
from pogo_team_optimizer.application.use_case import AnalyzeMetaUseCase
from pogo_team_optimizer.infrastructure.exporters.factory import ExporterFactory
from pogo_team_optimizer.infrastructure.repositories.csv_matrix_repository import (
    CsvSimulationMatrixRepository,
)
from pogo_team_optimizer.infrastructure.repositories.csv_switch_rankings_repository import (
    CsvSwitchRankingsRepository,
)
from pogo_team_optimizer.infrastructure.repositories.pokemon_json_repository import (
    PokemonJsonRepository,
)


DEFAULT_SWITCH_RANKINGS_PATH = "data/rankings/cp1500_all_switches_rankings.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze Battle Frontier matchup simulation matrices"
    )
    parser.add_argument(
        "--meta",
        default="bfretro",
        choices=["great", "crucible", "majestic", "euic", "master", "bfretro", "bfmaster"],
        help="Meta to analyze",
    )
    parser.add_argument(
        "--metas-config",
        default="data/metas.json",
        help="Path to metas configuration file",
    )
    parser.add_argument(
        "--pokemon-path",
        default="data/pokemon.json",
        help="Path to pokemon.json",
    )
    parser.add_argument(
        "--moves-path",
        default="data/moves.json",
        help="Path to moves.json",
    )
    parser.add_argument(
        "--switch-rankings-path",
        default=None,
        help="Path to PvPoke switch rankings CSV (optional)",
    )
    parser.add_argument(
        "--format",
        default="text",
        choices=["text", "markdown", "json", "csv", "excel", "pvpoke"],
        help="Output format",
    )
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--top-threats", type=int, default=10)
    parser.add_argument("--top-cores", type=int, default=5)
    parser.add_argument(
        "--safety-priority",
        default="medium",
        choices=["low", "medium", "high"],
        help="How strongly to enforce switch safety during optimization",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--restarts", type=int, default=250)
    return parser


def resolve_switch_rankings_path(
    cli_path: str | None, meta_switch_rankings_path: str | None
) -> str | None:
    if cli_path is not None:
        return cli_path
    if meta_switch_rankings_path is not None:
        return meta_switch_rankings_path
    return DEFAULT_SWITCH_RANKINGS_PATH


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.format in {"markdown", "json", "csv", "excel", "pvpoke"} and not args.output:
        parser.error("--output is required for markdown/json/csv/excel/pvpoke formats")

    if not Path(args.metas_config).exists():
        parser.error(f"Metas config not found: {args.metas_config}")
    if not Path(args.pokemon_path).exists():
        parser.error(f"Pokemon JSON not found: {args.pokemon_path}")
    if args.format == "pvpoke" and not Path(args.moves_path).exists():
        parser.error(f"Moves JSON not found: {args.moves_path}")

    meta_config = load_meta_config(args.metas_config, args.meta)
    missing_files = validate_matrix_files(meta_config.matrix_files)
    if missing_files:
        parser.error(
            "Missing simulation data for selected meta. "
            "Execution stopped. Missing files: " + ", ".join(missing_files)
        )
    missing_required_files = validate_required_files(meta_config.required_files)
    if missing_required_files:
        parser.error(
            "Missing required files for selected meta. "
            "Execution stopped. Missing files: " + ", ".join(missing_required_files)
        )

    simulation_repo = CsvSimulationMatrixRepository(list(meta_config.matrix_files))
    pokemon_repo = PokemonJsonRepository(args.pokemon_path)
    switch_rankings_repo = None
    switch_rankings_path = resolve_switch_rankings_path(
        args.switch_rankings_path,
        meta_config.switch_rankings_path,
    )
    if switch_rankings_path and Path(switch_rankings_path).exists():
        switch_rankings_repo = CsvSwitchRankingsRepository(switch_rankings_path)
    use_case = AnalyzeMetaUseCase(simulation_repo, pokemon_repo, switch_rankings_repo)
    result = use_case.execute(
        top_threats=args.top_threats,
        top_cores=args.top_cores,
        safety_priority=args.safety_priority,
        seed=args.seed,
        restarts=args.restarts,
    )
    result["meta"] = args.meta
    result["matrix_files"] = list(meta_config.matrix_files)

    exporter = ExporterFactory.create(
        args.format,
        pokemon_path=args.pokemon_path,
        moves_path=args.moves_path,
    )
    rendered = exporter.export(result, output_path=args.output)
    if rendered is not None:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
