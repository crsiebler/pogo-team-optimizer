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
from pogo_team_optimizer.infrastructure.repositories.battle_frontier_points_repository import (
    CsvBattleFrontierPointsRepository,
)
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
DEFAULT_OUTPUT_DIR = "data/output"
OUTPUT_FORMATS = ("text", "markdown", "json", "csv", "excel", "pvpoke")
OUTPUT_EXTENSIONS = {
    "text": "txt",
    "markdown": "md",
    "json": "json",
    "csv": "csv",
    "excel": "xlsx",
    "pvpoke": "pvpoke",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze Battle Frontier matchup simulation matrices"
    )
    parser.add_argument(
        "--meta",
        default="bfretro",
        choices=["great", "crucible", "majestic", "euic", "master", "bfretro", "bayou", "bfmaster"],
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
        help="Deprecated; all formats are exported every run",
    )
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated output files",
    )
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


def resolve_battle_frontier_points_path(
    meta_name: str, required_files: tuple[str, ...]
) -> str | None:
    if meta_name != "bfmaster":
        return None
    for path in required_files:
        if path.endswith("_cycle_points.csv"):
            return path
    return None


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.output is not None:
        parser.error("--output is deprecated; use --output-dir for generated artifacts")

    if not Path(args.metas_config).exists():
        parser.error(f"Metas config not found: {args.metas_config}")
    if not Path(args.pokemon_path).exists():
        parser.error(f"Pokemon JSON not found: {args.pokemon_path}")
    if not Path(args.moves_path).exists():
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
    battle_frontier_points_repo = None
    battle_frontier_points_path = resolve_battle_frontier_points_path(
        args.meta,
        meta_config.required_files,
    )
    if battle_frontier_points_path is not None:
        battle_frontier_points_repo = CsvBattleFrontierPointsRepository(battle_frontier_points_path)
    use_case = AnalyzeMetaUseCase(
        simulation_repo,
        pokemon_repo,
        switch_rankings_repo,
        battle_frontier_points_repo,
    )
    result = use_case.execute(
        top_threats=args.top_threats,
        top_cores=args.top_cores,
        safety_priority=args.safety_priority,
        seed=args.seed,
        restarts=args.restarts,
    )
    result["meta"] = args.meta
    result["matrix_files"] = list(meta_config.matrix_files)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for output_format in OUTPUT_FORMATS:
        exporter = ExporterFactory.create(
            output_format,
            pokemon_path=args.pokemon_path,
            moves_path=args.moves_path,
        )
        if output_format == "text":
            rendered = exporter.export(result)
            if rendered is not None:
                print(rendered)
                output_path = output_dir / f"{args.meta}.{OUTPUT_EXTENSIONS[output_format]}"
                output_path.write_text(rendered, encoding="utf-8")
            continue

        output_path = output_dir / f"{args.meta}.{OUTPUT_EXTENSIONS[output_format]}"
        exporter.export(result, output_path=str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
