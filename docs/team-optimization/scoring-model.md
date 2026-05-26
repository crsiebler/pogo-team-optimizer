# Weighted Scoring Model

The optimizer should use weighted strategic scores rather than a strict tier list. In `pogo-team-optimizer`, the ranking-aware weighted final score is one comparison input after safety and bulk guards plus the primary lineup objective, not the sole selector for recommended rosters.

## Priority Order

Use this order to set relative weights:

1. Synergy
2. Coverage
3. Safety
4. Consistency
5. Bulk
6. Defensive resistances vs weaknesses ratio
7. Offensive effectiveness vs resistance ratio
8. Role

## Roster Score

Normalize each component before combining. A recommended normalized range is `0.0` for poor and `1.0` for excellent.

```text
roster_score =
  synergy_weight * synergy_score +
  coverage_weight * coverage_score +
  safety_weight * safety_score +
  consistency_weight * consistency_score +
  bulk_weight * bulk_score +
  defensive_ratio_weight * defensive_ratio_score +
  offensive_ratio_weight * offensive_ratio_score +
  role_weight * role_score
```

Example starting weights:

```text
synergy: 0.24
coverage: 0.21
safety: 0.17
consistency: 0.13
bulk: 0.10
defensive_ratio: 0.07
offensive_ratio: 0.05
role: 0.03
```

These values are starting points, not fixed requirements. Tune them against known good teams, known bad teams, and real meta results.

In this project, default weights live in `RosterScoreWeights` and component diagnostics are emitted in deterministic `ROSTER_COMPONENT_ORDER`: `synergy`, `threat_coverage`, `safety`, `consistency`, `bulk`, `defensive_ratio`, `offensive_ratio`, and `role_fit`. Current roster-level synergy and role-fit components use neutral fallback diagnostics. Role fit affects recommended-lineup scoring and diagnostics when category rankings are wired into the use case, but it is not currently a direct roster-level optimizer input. Missing components use neutral or explicit missing diagnostics so partial ranking inputs remain explainable.

`TeamOptimizer` appends the ranking-aware final score after legacy tuple fields. `_comparison_key()` consumes candidate scores in this order: safety-floor deficit, safe-member deficit, bulk deficit, primary lineup objective score, ranking-aware final score, secondary lineup metrics, then legacy tie-breakers. Do not reorder existing tuple indexes consumed by use-case metrics or exporters.

## Lineup Score

Each ordered pick-3 lineup should have its own weighted score. Score the lineup as a battle plan, not as three independent Pokemon.

```text
lineup_score =
  synergy_weight * three_member_synergy +
  coverage_weight * lineup_coverage +
  safety_weight * lineup_safety +
  consistency_weight * lineup_consistency +
  bulk_weight * lineup_bulk +
  defensive_ratio_weight * lineup_defensive_ratio +
  offensive_ratio_weight * lineup_offensive_ratio +
  role_weight * lead_switch_closer_fit
```

Roster score should aggregate lineup quality:

- Best lineup score.
- Average of top N lineup scores.
- Number or percentage of viable lineups.
- Diversity of viable leads.
- Bench usefulness across viable lineups.
- Penalty for one-line teams where all success depends on a single obvious trio.

## Normalization

Do not combine raw values on incompatible scales. Normalize first:

- Convert ranks to percentiles or inverse rank quality.
- Convert matchup counts to rates.
- Convert type scores to bounded ratios.
- Cap outliers so one category cannot dominate by scale accident.
- Weight top-threat metrics separately from full-meta metrics.

PvPoke ranking scores are already on a `0` to `100` scale where `100` is the best Pokemon in the league and category. Prefer normalized score values over raw rank positions when available because rank gaps are not uniform.

Ranking-aware scoring should consume normalized PvPoke category values, ranking-pool matrix indices for top-threat weighting, normalized consistency category scores where available, shield-path stability as the current bait-dependence proxy, and neutral move DPE fallback until move power and energy data are modeled.

When combining PvPoke categories, geometric mean is often more appropriate than arithmetic mean because category scores are percentages and well-roundedness matters. Geometric mean penalizes a Pokemon that is excellent in one category but poor in another more than an arithmetic mean would.

When weighting matchups, use opponent importance where possible. PvPoke weights Battle Ratings by opponent average so good performance against powerful Pokemon matters more than good performance against weak Pokemon. Optimizers should follow the same principle for top-threat pools and meta-weighted coverage.

## Move Score Inputs

Move scores should account for more than raw type effectiveness:

- Damage and energy cost.
- Damage per energy.
- Energy generation for fast moves.
- Stat changes.
- Usage across matchups.
- Value into significant meta targets.
- Whether a second charged move improves meaningful matchups.

Do not assume a broad theoretical movepool is fully available in one battle. Pokemon can carry one fast move and two charged moves, so score the selected moveset rather than every possible optimal move across all matchups.

## Hard Constraints

Use hard constraints only for validity and legality:

- Duplicate base species rules.
- League eligibility.
- Tournament point caps.
- Required or banned Pokemon.
- Required roster size.

Do not use hard constraints for strategic concepts like role balance or type diversity unless the format explicitly requires them.
