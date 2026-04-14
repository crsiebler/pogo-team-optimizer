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
PYTHONPATH=src python -m pogo_team_optimizer.cli.main --meta crucible --format text
```

For `markdown`, `json`, `csv`, `excel`, and `pvpoke`, pass `--output`.

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
- Matrix CSVs must align on row/column labels across shield scenarios.
- `AnalyzeMetaUseCase` expects repository dependencies through interfaces.
- `pvpoke` export requires both `pokemon.json` and `moves.json`.
- Non-text outputs require explicit output file paths.
- Meta-specific auxiliary inputs belong in `data/metas.json` via optional `switch_rankings_path` and `required_files`; validate them in the CLI before constructing repositories.
- Switch rankings resolution in the CLI is ordered as explicit `--switch-rankings-path` override, then per-meta `switch_rankings_path`, then the legacy Great League default path.
- Battle Frontier point files should live under `data/battle_frontier/` with `species,points` headers, use names normalized like `parse_species()`, and rely on repository fallback-to-`0` for species omitted from the current cycle.
- Battle Frontier legality belongs in `TeamOptimizer`; wire per-row point costs from the CLI/use case into the optimizer so both initial seeding and swap search share the same legality checks.
- Battle Frontier output metrics belong in `recommended_team.metrics`; keep them optional and have human-readable exporters render a conditional legality section so non-`bfmaster` metas do not need placeholder fields.

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
