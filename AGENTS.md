# AGENTS.md
Guidance for autonomous coding agents working in this repository.

## Project Snapshot
- Project: `pogo-team-optimizer`
- Language: Python 3.12+
- Source root: `src/`
- Test root: `tests/`
- CLI entrypoint: `python -m pogo_team_optimizer.cli.main`
- Build backend: `setuptools` (`pyproject.toml`)

## Environment
- Preferred env definition: `environment.yml`
- Included tools: `ruff`, `mypy`, `pytest`, `pytest-cov`, `pre-commit`

Typical setup:
```bash
conda env create -f environment.yml
conda activate pogo-team-optimizer
```

Important: run commands with `PYTHONPATH=src`.

## Build / Lint / Test Commands
Use Makefile targets when available:
```bash
make lint
make typecheck
make test
make coverage
make all
```

Equivalent direct commands:
```bash
PYTHONPATH=src python -m ruff check src tests
PYTHONPATH=src python -m mypy src
PYTHONPATH=src python -m pytest
PYTHONPATH=src python -m pytest --cov=src --cov-report=term-missing
```

## Single-Test Commands (Important)
Fast iteration examples:
```bash
# one file
PYTHONPATH=src python -m pytest tests/unit/test_normalization.py

# one test function
PYTHONPATH=src python -m pytest tests/unit/test_normalization.py::test_parse_species_strips_moves_and_ivs

# keyword filter
PYTHONPATH=src python -m pytest -k normalization

# fail fast
PYTHONPATH=src python -m pytest -x

# verbose targeted run
PYTHONPATH=src python -m pytest -vv tests/unit/test_csv_repository.py::test_csv_repository_loads_three_scenarios
```

## CLI Commands
Convenience targets:
```bash
make run
make run-json
make run-md
make run-pvpoke
```

Direct invocation example:
```bash
PYTHONPATH=src python -m pogo_team_optimizer.cli.main --meta bayou --format text
```

Each CLI run emits all supported formats; use `--output-dir` to control the destination.

## Architecture and Boundaries
Respect the existing layers:
- `pogo_team_optimizer/domain`: interfaces and immutable domain models
- `pogo_team_optimizer/application`: use cases, optimization, analyzers, normalization
- `pogo_team_optimizer/infrastructure`: repositories and exporters
- `pogo_team_optimizer/cli`: argparse parsing, validation, wiring

Boundary rules:
- Keep core business logic out of CLI and exporters.
- Keep file I/O in infrastructure/boundary modules.
- Inject repository dependencies into use cases via interfaces.
- Add new output formats through exporter classes + `ExporterFactory`.

## Code Style Guidelines

### Formatting
- Follow Ruff defaults and project line length (`100`).
- Prefer readable, explicit code over compact clever code.
- Keep functions small and purpose-focused.

### Imports
- Import grouping order:
  1. `from __future__ import annotations` (if used)
  2. Python standard library
  3. Local package imports (`pogo_team_optimizer...`)
- Separate groups with one blank line.
- Avoid wildcard imports.

### Typing
- Mypy is strict for `src`; do not loosen typing.
- Add explicit return types on non-trivial/public functions.
- Prefer concrete typing (`list[str]`, `tuple[int, ...]`).
- Use explicit optional unions (`X | None`).
- Keep tuple-based scoring/type patterns consistent with existing code.

### Naming
- Modules/files: `snake_case.py`
- Variables/functions: `snake_case`
- Classes/enums/dataclasses: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Test files: `test_*.py`
- Test functions: `test_<behavior>()`

### Error Handling
- Raise `ValueError` for invalid config/input/data (existing convention).
- Include actionable context in messages (path, meta, token, etc.).
- Fail fast on invalid CLI arguments and missing files.
- Avoid silent fallback behavior unless intentional and documented.

### Data and Contracts
- Prefer frozen dataclasses for immutable domain entities.
- Preserve output schema keys expected by exporters/tests.
- When changing result fields, update all impacted exporters and tests.

## Testing Guidelines
- Add or update tests for each logic change.
- Unit tests live in `tests/unit`.
- Integration tests live in `tests/integration`.
- Keep optimizer-related tests deterministic with explicit seeds.
- Cover parsing edge cases and matrix label alignment behavior.

Recommended local gate before completion:
```bash
make lint
make typecheck
make test
```

## Repository-Specific Notes
- Project-agnostic Pokemon GO Battle League optimization guidance lives in `docs/pokemon-go-team-optimization.md`; read it before changing roster or lineup scoring strategy.
- Detailed optimization subdocs live under `docs/team-optimization/`, including `scoring-model.md`, `lineup-structures.md`, `coverage-threat-pools.md`, `safety-consistency-bulk.md`, `type-effectiveness.md`, `role-scoring.md`, `data-inputs.md`, and `validation.md`.
- OpenCode skill `gbl-optimizer` lives in `.opencode/skills/gbl-optimizer/SKILL.md`; use it when changing GBL optimizer scoring, show-6 pick-3 lineups, PvPoke ranking inputs, type effectiveness, coverage, safety, consistency, bulk, roles, or ABC/ABB/ABA strategy.
- Type effectiveness implementation guidance is in `docs/team-optimization/type-effectiveness.md`, and the Pokemon GO type chart source data is `data/type-effectiveness.json`.
- Matrix CSVs must align on row/column labels across shield scenarios.
- `AnalyzeMetaUseCase` expects repository dependencies through interfaces.
- `pvpoke` export requires both `pokemon.json` and `moves.json`.
- CLI runs emit all supported output formats to `--output-dir`; do not use deprecated `--output`.
- Meta-specific PvPoke ranking inputs belong in `data/metas.json` via typed `ranking_paths` and optional `full_meta_ranking_paths` keyed by `RankingCategory`; keep legacy `switch_rankings_path` as a compatibility shim only.
- Validate all configured ranking paths in the CLI before constructing repositories; switch rankings resolution remains explicit `--switch-rankings-path`, then per-meta `ranking_paths.switches`, then the legacy Great League default path.
- Ranking threat pools belong in `application/ranking_pools.py`; align ranking profiles to normalized matrix opponent labels, deduplicate by `parse_base_species()` like the optimizer, and keep missing ranking entries deterministic instead of failing.
- Ranking-aware weighted score structures belong in `application/scoring.py`; keep component order deterministic, missing components neutral with diagnostics, and default weights centralized in `RosterScoreWeights`.
- PvPoke category score normalization belongs in `application/scoring.py`; keep raw `RankingRow.score` values for diagnostics, put derived valid `normalized_score` values on a `0.0` to `1.0` scale, store invalid values as `None`, and use neutral `0.5` fallback for missing, invalid, or degenerate category lookups.
- Battle Frontier point files should live under `data/battle_frontier/` with `species,points` headers, use names normalized like `parse_species()`, and rely on repository fallback-to-`0` for species omitted from the current cycle.
- Battle Frontier legality belongs in `TeamOptimizer`; wire per-row point costs from the CLI/use case into the optimizer so both initial seeding and swap search share the same legality checks.
- Battle Frontier output metrics belong in `recommended_team.metrics`; keep them optional and have human-readable exporters render a conditional legality section so non-`bfmaster` metas do not need placeholder fields.
- Battle Frontier lineup point diagnostics are optional result fields assembled in `AnalyzeMetaUseCase` from `application/lineups.py`; do not reject individual pick-3 lineups for point totals in the MVP.
- Ordered bring-6 pick-3 lineup enumeration belongs in `application/lineups.py`; keep lead order distinct and canonicalize the unordered back pair by sorted row index.
- Ordered lineup resource-path scoring belongs in `application/lineups.py`; keep the fixed paths as lead 1/back 1, lead 2/back 0, and lead 0/back 2, with lineup thresholds of score greater than `600` for dominating and less than `400` for overwhelming losses.
- Ordered lineup role-fit scoring belongs in `application/lineups.py` and should consume normalized `RankingRow.normalized_score` values from a use-case-normalized `RankingProfile`; leads use `leads`, unordered backs are averaged across `switches`/`closers` plus secondary role categories, and role weight stays low (`0.03`) versus resource-path matchup score.
- Six-Pokemon roster objective scoring belongs in `TeamOptimizer` consuming lineup-depth metrics from `application/lineups.py`; append new optimizer score tuple fields instead of reordering existing indexes consumed by use-case metrics and exporters.
- Meta-relative bulk viability belongs in `TeamOptimizer._comparison_key()` as a below-floor penalty before lineup objective fields; derive the floor from the loaded candidate pool and do not treat it as a legality filter.
- `TeamOptimizer` caches pure score results per optimizer instance: full team scores by sorted row-index identity and ordered lineup mean scores by `OrderedLineup`; do not cache comparison keys because safety and policy inputs vary per call.
- `TeamOptimizer.optimize(workers=...)` uses the existing single-process restart loop for `workers=1`; process-based parallelism is preferred over threads for CPU-bound optimizer work, should split restart batches with deterministic per-worker seeds, cap worker counts via `MAX_OPTIMIZER_WORKERS`, and reduce results through `_comparison_key()` in the parent.
- Structured `recommended_lineups` assembly belongs in `AnalyzeMetaUseCase`; keep ranking and diagnostics based on `application/lineups.py`, and keep CLI/exporters from computing lineup scores.
- CLI lineup count control is `--top-lineups` with a maximum of `10`; pass it as `top_lineups` to `AnalyzeMetaUseCase` and do not compute safe-core rankings during normal execution.
- Bench utility diagnostics belong in `application/lineups.py` and stay diagnostic-only; normal `AnalyzeMetaUseCase` results keep `recommended_team.bench_utility` empty unless actionable Battle Frontier warnings are emitted.
- ABC/ABB/ABA lineup shape labels are heuristic diagnostics from `application/lineups.py`; expose them on `recommended_lineups` but never use them for lineup scoring, roster ranking, or tie-breaking.
- CSV lineup-aware exports preserve the `section,key,value` schema using `recommended_lineup`, `recommended_lineup_resource_path`, `bench_utility`, and `bench_utility_warning` sections; Excel uses dedicated `Lineups`, `Lineup Resources`, `Bench Utility`, and `Bench Warnings` sheets.
- Legacy full-six dominate and overwhelming metrics must not be presented as battle coverage; actual battle interpretation belongs to ordered pick-3 lineup diagnostics and their fixed resource paths.
- Human-readable text and Markdown reports should keep normal output focused on Recommended Bring-6 Roster, Team Analysis, Recommended Lineups, actionable warnings, and Potential Threats; do not reintroduce standalone Coverage, Safe Cores, full-roster Coverage, or Resource / Shield Safety sections.
- Bench utility diagnostics remain structured data, but normal text and Markdown output should render them only when actionable warnings exist.

## Cursor / Copilot Rule Files
Checked repository-local instruction files:
- `.cursor/rules/`: not found
- `.cursorrules`: not found
- `.github/copilot-instructions.md`: not found

If these files are added later, treat them as higher-priority policy and update this document.

## Agent Checklist
Before coding:
- Read the touched modules fully.
- Confirm correct architectural layer for the change.
- Add or update tests first when practical.

Before finishing:
- Run focused tests for changed code.
- Run `make typecheck`.
- Run `make lint` and `make test` for non-trivial changes.
- Verify no accidental CLI or exporter schema regressions.
