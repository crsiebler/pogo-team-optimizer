from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from pogo_team_optimizer.application.meta_config import (
    load_meta_config,
    validate_matrix_files,
    validate_ranking_files,
    validate_required_files,
)
from pogo_team_optimizer.application.optimizer import MAX_OPTIMIZER_WORKERS
from pogo_team_optimizer.application.use_case import AnalyzeMetaUseCase
from pogo_team_optimizer.domain.models import RankingCategory
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
from pogo_team_optimizer.infrastructure.repositories.move_json_repository import MoveJsonRepository
from pogo_team_optimizer.infrastructure.repositories.pokemon_json_repository import (
    PokemonJsonRepository,
)
from pogo_team_optimizer.infrastructure.repositories.type_effectiveness_json_repository import (
    TypeEffectivenessJsonRepository,
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
LOGGER = logging.getLogger(__name__)
SUPPORTED_METAS = (
    "great",
    "majestic",
    "euic",
    "naic",
    "master",
    "bfretro",
    "bayou",
    "spellcraft",
    "bfmaster",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze Battle Frontier matchup simulation matrices"
    )
    parser.add_argument(
        "--meta",
        default="bfretro",
        choices=SUPPORTED_METAS,
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
        "--type-effectiveness-path",
        default="data/type-effectiveness.json",
        help="Path to type-effectiveness.json",
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
    parser.add_argument("--top-lineups", type=int, default=5)
    parser.add_argument(
        "--safety-priority",
        default="medium",
        choices=["low", "medium", "high"],
        help="How strongly to enforce switch safety during optimization",
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--restarts", type=int, default=250)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Log execution progress to stderr for diagnosing slow runs",
    )
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
    diagnostics_enabled = args.diagnostics or os.environ.get(
        "POGO_TEAM_OPTIMIZER_DIAGNOSTICS"
    ) in {"1", "true", "TRUE", "yes", "YES"}
    if diagnostics_enabled:
        logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(name)s: %(message)s")
    if not 1 <= args.top_lineups <= 10:
        parser.error("--top-lineups must be between 1 and 10")
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if args.workers > MAX_OPTIMIZER_WORKERS:
        parser.error(f"--workers must be at most {MAX_OPTIMIZER_WORKERS}")
    LOGGER.info(
        "starting analysis meta=%s restarts=%s workers=%s top_threats=%s top_lineups=%s",
        args.meta,
        args.restarts,
        args.workers,
        args.top_threats,
        args.top_lineups,
    )

    if args.output is not None:
        parser.error("--output is deprecated; use --output-dir for generated artifacts")

    if not Path(args.metas_config).exists():
        parser.error(f"Metas config not found: {args.metas_config}")
    if not Path(args.pokemon_path).exists():
        parser.error(f"Pokemon JSON not found: {args.pokemon_path}")
    if not Path(args.moves_path).exists():
        parser.error(f"Moves JSON not found: {args.moves_path}")
    if not Path(args.type_effectiveness_path).exists():
        parser.error(f"Type effectiveness JSON not found: {args.type_effectiveness_path}")

    meta_config = load_meta_config(args.metas_config, args.meta)
    LOGGER.info("loaded meta config matrix_files=%s", ",".join(meta_config.matrix_files))
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
    ranking_paths_for_validation = dict(meta_config.ranking_paths)
    if args.switch_rankings_path is not None:
        ranking_paths_for_validation[RankingCategory.SWITCHES] = args.switch_rankings_path
    missing_ranking_files = validate_ranking_files(
        ranking_paths_for_validation,
        meta_config.full_meta_ranking_paths,
    )
    if missing_ranking_files:
        parser.error(
            "Missing configured ranking files for selected meta. "
            "Execution stopped. Missing files: " + ", ".join(missing_ranking_files)
        )

    simulation_repo = CsvSimulationMatrixRepository(list(meta_config.matrix_files))
    pokemon_repo = PokemonJsonRepository(args.pokemon_path)
    move_repo = MoveJsonRepository(args.moves_path)
    type_effectiveness_repo = TypeEffectivenessJsonRepository(args.type_effectiveness_path)
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
        LOGGER.info("loading Battle Frontier points path=%s", battle_frontier_points_path)
        battle_frontier_points_repo = CsvBattleFrontierPointsRepository(battle_frontier_points_path)
    use_case = AnalyzeMetaUseCase(
        simulation_repo,
        pokemon_repo,
        switch_rankings_repo,
        battle_frontier_points_repo,
        move_repo,
        type_effectiveness_repo,
    )
    LOGGER.info("starting use case execution")
    result = use_case.execute(
        top_threats=args.top_threats,
        top_lineups=args.top_lineups,
        safety_priority=args.safety_priority,
        seed=args.seed,
        restarts=args.restarts,
        workers=args.workers,
    )
    LOGGER.info("completed use case execution")
    result["meta"] = args.meta
    result["matrix_files"] = list(meta_config.matrix_files)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for output_format in OUTPUT_FORMATS:
        LOGGER.info("exporting format=%s", output_format)
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
                LOGGER.info("exported format=%s output=%s", output_format, output_path)
            continue

        output_path = output_dir / f"{args.meta}.{OUTPUT_EXTENSIONS[output_format]}"
        exporter.export(result, output_path=str(output_path))
        LOGGER.info("exported format=%s output=%s", output_format, output_path)
    LOGGER.info("analysis complete meta=%s output_dir=%s", args.meta, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
