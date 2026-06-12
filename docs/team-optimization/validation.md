# Validation Strategy

Validate the optimizer with known battle concepts, known meta teams, and controlled edge cases.

## Required Checks

- Dual-type effectiveness multiplication is correct.
- Pokemon GO immunity-style interactions use `0.39x`.
- Top-threat coverage is scored separately from full-meta coverage.
- Weighted scoring allows tradeoffs instead of acting like a tier list.
- Synergy is weighted above coverage.
- Coverage is weighted above safety.
- Role scoring does not dominate the result.
- ABB and ABA structures can score well when strategically coherent.
- ABA shared weakness is penalized when it creates lead-alignment fragility.
- ABA shared strength can be rewarded when it creates redundant answers.
- Teams with severe shared weaknesses are penalized.
- Teams with one Pokemon covering too many key threats are flagged as fragile.
- Multiple viable lineups are preferred over one obvious best line.
- Candidate rows with blank or non-numeric matchup cells in any configured shield matrix are excluded before optimization.
- Candidate rows without a normalized active `overall` ranking match are excluded before optimization.
- Ranked threat pools intersect ranking profiles with simulation target columns and exclude unranked targets from threat scoring.
- Full-team diagnostics use soft shield aggregation with `0.30`, `0.50`, and `0.20` weights for 0-, 1-, and 2-shield scores, renormalized when needed.
- Full-team A-F grades and lower-is-better Threat Score are validated as diagnostics while full bring-6 quality remains the primary selection objective.

## Useful Fixtures

Create small deterministic fixtures for:

- A team with strong full-roster coverage but poor pick-3 lineup synergy.
- A team with one excellent trio and three dead roster slots.
- An ABB lineup where the A Pokemon correctly covers the B pair.
- An ABB lineup where the shared weakness is not covered.
- An ABA shared-weakness lineup into a common lead threat.
- An ABA shared-strength lineup with redundant answers.
- A roster with strong coverage but poor bulk.
- A roster with high type diversity but poor matrix performance.

In this repository, use `tests/fixtures/us031_weighted_scoring/` for compact ranking-aware regressions. It includes category ranking CSVs, aligned three-shield matrices, Pokemon typing/stat data, move data, and type-effectiveness data designed to avoid large production ranking inputs in unit tests.

Optimizer tests should use explicit seeds. Missing ranking entries, duplicate normalized species, tied scores, and invalid ranking values should produce deterministic ordering or neutral fallback behavior rather than nondeterministic failures.

Multiprocessing validation should keep `workers=1` on the existing single-process path and use process-based restart batches for `workers>1`. Cache tests should verify deterministic scoring-context fingerprints include ranking-aware inputs, and should avoid using giant nested matrices directly as hot cache-key members.

## Explainability Review

Every recommendation should make sense to a human reviewer. If the optimizer returns a surprising team, diagnostics should show why:

- Which top threats are covered.
- Which top threats are risky.
- Which lineups are most viable.
- Which shared weaknesses exist.
- Which Pokemon are single points of failure.
- Which role assumptions were used.

If diagnostics cannot explain the recommendation, improve the score breakdown before tuning weights.

Review score breakdowns as optimizer evidence and explanation payloads as diagnostics. Exporter text should summarize high-value diagnostics without restoring deprecated standalone Safe Cores, full-roster Coverage, or Resource / Shield Safety sections. Scoring weights, thresholds, shield aggregation values, and grade cutoffs are internal implementation details; validate them with regression tests instead of exposing them as CLI tuning knobs.
