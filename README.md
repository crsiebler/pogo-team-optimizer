# pogo-team-optimizer

`pogo-team-optimizer` analyzes Pokemon GO PvP simulation matrices and recommends strong six-member teams for a selected meta.

It evaluates matchup coverage across shield scenarios, identifies fragile matchups, and exports reports in multiple formats.

## Features

- Optimize a 6-Pokemon team from simulation matrix data using ordered pick-3 lineups
- Recommend playable lead/back-pair lineups from the selected bring-6 roster
- Report lineup resource-path safety across shield scenarios
- Explain bench utility, warnings, and Battle Frontier point diagnostics when available
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

The Makefile runs commands through the `pogo-team-optimizer` Conda environment by
default. Use these targets for the local quality gate:

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

Basic run:

```bash
PYTHONPATH=src python -m pogo_team_optimizer.cli.main --meta crucible
```

Supported metas include `bayou`, `bfretro`, `bfmaster`, `crucible`, `euic`, `great`,
`majestic`, `master`, `naic`, and `spellcraft`.

Each CLI execution runs the optimizer once, prints the text report, and writes every supported
format to `data/output/`:

```bash
PYTHONPATH=src python -m pogo_team_optimizer.cli.main --meta crucible
```

Generated files use the selected meta name: `<meta>.txt`, `<meta>.md`, `<meta>.json`,
`<meta>.csv`, `<meta>.xlsx`, and `<meta>.pvpoke`. Use `--output-dir` to write them elsewhere.

The Make target uses the same single-run workflow:

```bash
make run META=bayou
make run META=bayou WORKERS=2
make run META=bayou DIAGNOSTICS=1
```

If `META` is omitted, Makefile run targets default to `bfmaster`.

Useful CLI controls:

- `--top-lineups N` controls how many recommended ordered pick-3 lineups appear in
  reports. The CLI accepts values from `1` through `10`; the Makefile run target uses
  `--top-lineups 10`.
- `--workers N` runs optimizer restarts across process workers. `WORKERS=N` passes the
  same value through `make run`.
- `--diagnostics` enables progress and diagnostic logging. `DIAGNOSTICS=1` passes this
  flag through `make run`; the `POGO_TEAM_OPTIMIZER_DIAGNOSTICS` environment variable
  enables the same logging for direct CLI invocations.

Multiprocessing is process-based, not thread-based. Worker runs split optimizer restarts
into deterministic batches and reduce the best result in the parent process, which keeps
CPU-bound scoring work parallel without parallelizing individual matchup cells or lineup
resource-path calculations.

## Interpreting Lineup-Aware Results

The optimizer recommends a bring-6 roster, but roster scoring is based on ordered pick-3
lineups rather than treating all six Pokemon as simultaneously available in battle. Each
six-Pokemon roster produces exactly `60` ordered lineups: `6` possible leads multiplied by
`10` unordered back pairs from the remaining five Pokemon.

Each ordered lineup has one lead and a canonical unordered back pair. Lead order remains
meaningful, so `A` leading with `B/C` is different from `B` leading with `A/C`, while the
back pair `B/C` is the same as `C/B` for the same lead.

Lineup scoring uses fixed resource paths that connect the lead's shield use to the backs'
remaining shields:

- Balanced: lead `1` shield, backs `1` shield
- Shield-spend: lead `2` shields, backs `0` shields
- Shield-save: lead `0` shields, backs `2` shields

For each matchup in a resource path, the back-pair result uses the better score from either
back Pokemon. Lineup diagnostics count dominating matchups with score `> 600` and
overwhelming losses with score `< 400`.

The report includes recommended lineups as viable options for multi-battle play, not as a
single mandatory default lineup. Bench utility explains how often each roster member appears
in viable lineups and classifies members as core, flexible, specialist, low utility, or
unbringable. Warnings call out low-usage or unbringable roster members and should be read as
diagnostic caveats, not hard failures unless the output says otherwise.

Normal text and Markdown reports intentionally focus on Recommended Bring-6 Roster, Team
Analysis, Recommended Lineups, actionable warnings, and Potential Threats. They omit
standalone Safe Cores, full-roster Coverage, and Resource / Shield Safety sections because
actual battle interpretation belongs to ordered pick-3 lineup diagnostics. Bench utility
appears in human-readable output only when there are actionable warnings.

Structured diagnostics are retained where they remain useful for automation and analysis.
JSON includes the full result payload, CSV keeps stable sections such as
`recommended_lineup`, `recommended_lineup_resource_path`, `bench_utility`, and
`bench_utility_warning`, and Excel uses dedicated sheets for lineup and bench diagnostics.

For Battle Frontier metas, optional diagnostics show roster point totals, lineup point totals,
free or low-point usage rates, high-point usage rates, and point-aware bench warnings. The MVP
keeps Battle Frontier legality at the six-roster level and does not reject individual pick-3
lineups for point totals.

ABC, ABB, and ABA lineup labels are heuristic diagnostics for interpreting team shape. They
are not scoring inputs, ranking inputs, or tie-breakers in the MVP.

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
- Legacy full-six dominate and overwhelming diagnostics are not battle coverage for actual
  pick-3 play; use the ordered lineup sections for battle interpretation.

## Contributing

For code changes, follow this local quality gate before opening a PR:

```bash
make lint
make typecheck
make test
```

Recommended workflow:

- Add or update tests for each logic change
- Use focused test runs during iteration, then run the full suite
- Keep strict typing clean in `src/` (mypy strict mode)
