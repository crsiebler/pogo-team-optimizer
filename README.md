# pogo-team-optimizer

`pogo-team-optimizer` analyzes Pokemon GO PvP simulation matrices and recommends strong six-member teams for a selected meta.

It evaluates matchup coverage across shield scenarios, identifies fragile matchups, and exports reports in multiple formats.

## Features

- Optimize a 6-Pokemon team from simulation matrix data
- Rank safe 3-member cores from the recommended team
- Report coverage by shield scenario
- Highlight threats with single-cover and no-cover fragility
- Export as `text`, `markdown`, `json`, `csv`, `excel`, or `pvpoke`

## Project Layout

- `src/pogo_team_optimizer/` - application code
- `tests/unit/` - unit tests
- `tests/integration/` - integration tests
- `data/` - metas config and simulation/input data

## Environment Setup

This project targets Python 3.12+.

```bash
conda env create -f environment.yml
conda activate pogo-team-optimizer
```

All commands should run with `PYTHONPATH=src`.

## Development Commands

```bash
make lint
make typecheck
make test
make coverage
make all
```

Direct equivalents:

```bash
PYTHONPATH=src python -m ruff check src tests
PYTHONPATH=src python -m mypy src
PYTHONPATH=src python -m pytest
PYTHONPATH=src python -m pytest --cov=src --cov-report=term-missing
```

## Running the CLI

Basic text output:

```bash
PYTHONPATH=src python -m pogo_team_optimizer.cli.main --meta crucible --format text
```

Supported metas include `bayou`, `bfretro`, `great`, `bfmaster`, and `crucible`.

Use `--output` for non-text formats (`markdown`, `json`, `csv`, `excel`, `pvpoke`):

```bash
PYTHONPATH=src python -m pogo_team_optimizer.cli.main --meta crucible --format json --output analysis.json
```

Make targets are also available:

```bash
make run META=bayou
make run-json META=bayou
make run-md META=bayou
make run-pvpoke META=bayou
```

If `META` is omitted, Makefile run targets default to `bfmaster`.

## Fast Test Iteration

```bash
# single file
PYTHONPATH=src python -m pytest tests/unit/test_normalization.py

# single test
PYTHONPATH=src python -m pytest tests/unit/test_normalization.py::test_parse_species_strips_moves_and_ivs
```

## Notes

- Keep matrix CSV row/column labels aligned across all shield files for a meta.
- `pvpoke` export requires both `data/pokemon.json` and `data/moves.json`.

## Contributing

For code changes, follow this local quality gate before opening a PR:

```bash
make typecheck
make lint
make test
```

Recommended workflow:

- Add or update tests for each logic change
- Use focused test runs during iteration, then run the full suite
- Keep strict typing clean in `src/` (mypy strict mode)
