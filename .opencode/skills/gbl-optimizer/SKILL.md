---
name: gbl-optimizer
description: Use when changing Pokemon GO Battle League optimizer scoring, show-6 pick-3 lineups, PvPoke ranking inputs, type effectiveness, coverage, safety, consistency, bulk, roles, or ABC/ABB/ABA strategy.
---

# GBL Optimizer

Use this skill when implementing, refactoring, reviewing, or planning Pokemon GO Battle League team optimization logic.

## Required Reading

Before changing roster or lineup scoring, read:

- `docs/pokemon-go-team-optimization.md`
- `docs/team-optimization/scoring-model.md`
- `docs/team-optimization/lineup-structures.md`
- `docs/team-optimization/coverage-threat-pools.md`
- `docs/team-optimization/safety-consistency-bulk.md`
- `docs/team-optimization/type-effectiveness.md`
- `docs/team-optimization/role-scoring.md`
- `docs/team-optimization/data-inputs.md`
- `docs/team-optimization/validation.md`

Use `data/type-effectiveness.json` as the source of truth for Pokemon GO type chart values.

## Optimization Principles

The optimizer should use weighted strategic scores rather than a strict tier list. In this repository, `TeamOptimizer._comparison_key()` applies safety-floor deficit, safe-member deficit, and bulk deficit before the primary lineup objective, then considers the ranking-aware weighted final score, secondary lineup metrics, and legacy tie-breakers.

Weight strategy in this order:

1. Synergy
2. Coverage
3. Safety
4. Consistency
5. Bulk
6. Defensive resistances vs weaknesses ratio
7. Offensive effectiveness vs resistance ratio
8. Role

Score ordered pick-3 lineups as playable battle plans. Then aggregate lineup quality into show-6 roster quality.

## Domain Checks

When changing scoring, check for:

- Multiple viable lineups, not one obvious trio.
- Top-threat coverage separately from full-meta coverage.
- ABA shared weakness risk, especially when the shared weakness can appear in the lead.
- ABB lineups that are intentionally baiting or covering a shared weakness.
- Defensive type exposure weighted by meta relevance.
- Offensive move coverage using actual selected move types.
- Safety via overwhelming losses, no-answer threats, and single-answer threats.
- Consistency via bait dependence, move DPE, shield stability, and PvPoke consistency data when available.
- Bulk using stat product or `defense * hp / attack` when direct stat product is unavailable.
- Role fit using PvPoke Leads, Switches, Closers, Chargers, Attackers, and Consistency exports when available.
- Current roster-level role fit is a neutral fallback diagnostic; role fit affects recommended-lineup scoring and diagnostics when category rankings are wired into the use case, not direct roster-level optimizer comparison.

## Architecture Boundaries

- Keep optimization and scoring logic in the application layer.
- Keep CLI code limited to argument parsing, validation, and dependency wiring.
- Keep file parsing in infrastructure repositories.
- Keep exporters presentation-only.
- Inject repositories through interfaces rather than reading files from scoring code.
- Load category ranking CSVs in infrastructure repositories, then normalize scores and build active-meta, full-meta, and top-threat pools in application services.
- Keep weighted roster and lineup component ordering deterministic, with neutral fallback diagnostics for missing or invalid ranking inputs.
- Assemble ranking-aware explainability in `AnalyzeMetaUseCase`; exporters must render score breakdowns, threats, role assumptions, and shared-weakness diagnostics without recomputing them.
- Preserve optimizer cache and multiprocessing boundaries: cache keys must include deterministic scoring-context fingerprints, and process workers should receive picklable data snapshots rather than repository instances.
- Do not reintroduce standalone Safe Cores, full-roster Coverage, or Resource / Shield Safety sections in normal text or Markdown output.

## Testing Expectations

For scoring changes, add or update tests first when practical.

Cover:

- Controlled lineup scoring edge cases.
- ABC, ABB, and ABA behavior.
- Shared weakness penalties and shared strength rewards.
- Top-threat vs full-meta coverage weighting.
- Ranking-pool alignment to matrix labels and `parse_base_species()` deduplication.
- Neutral fallback behavior for missing, invalid, and degenerate PvPoke category scores.
- Type effectiveness dual-type multiplication.
- Deterministic optimizer output for fixed seeds.
- Deterministic `workers=1` and `workers>1` behavior when ranking-aware scoring inputs are present.
- Regression cases where paper coverage differs from playable pick-3 synergy.

Prefer `tests/fixtures/us031_weighted_scoring/` for compact ranking-aware regressions instead of production ranking CSVs.

Run focused tests, then `make typecheck` and `make lint`. Run `make test` for non-trivial optimizer changes.
