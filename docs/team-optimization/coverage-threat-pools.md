# Coverage And Threat Pools

Coverage measures how well a roster or lineup handles expected opponents. It should be measured against both a prioritized top-threat pool and a broader full-meta pool.

## Top-Threat Pool

The top-threat pool is a smaller, high-priority set of Pokemon that most strongly affects practical viability.

Sources may include:

- Top N PvPoke rankings.
- Usage-weighted threats.
- Tournament results.
- Curated meta cores.
- Pokemon above a score or rank threshold.

Top-threat coverage should carry more weight than full-meta coverage. A team that loses hard to a common top threat should be penalized even if it covers many rare Pokemon.

In `pogo-team-optimizer`, top threats are built in `application/ranking_pools.py` from the active meta ranking profile and matrix labels. Pool construction normalizes matrix labels with the same species helpers used by the optimizer, deduplicates by `parse_base_species()`, prefers finite PvPoke scores from `0` through `100`, and keeps missing scores deterministic rather than failing.

## Full-Meta Pool

The full-meta pool is the broader eligible field.

Use it to detect:

- Broad typing holes.
- Unexpected hard losses.
- Over-specialized rosters.
- Coverage that only works against the top of rankings.

Full-meta coverage matters, but it should not dominate top-threat coverage.

The application pool builder can construct a full-meta pool when a separate full-meta ranking profile is supplied. In current normal CLI execution, `full_meta_ranking_paths` are parsed and validated but not loaded as a separate scoring profile; broad full-meta scoring uses all matchup matrix columns. If full-meta rankings are absent or not wired, scoring should remain deterministic and use explicit neutral or matrix-column fallback behavior.

## Coverage Metrics

Useful metrics include:

- Number of threats with at least one answer.
- Number of threats with at least two answers.
- Number of no-answer threats.
- Number of single-answer threats.
- Weighted matchup score by shield scenario.
- Worst shield path for each threat.
- Core coverage against common two- or three-Pokemon cores.

## Lineup Coverage

Coverage should be scored per lineup, not only per six-Pokemon roster.

For each ordered lineup, ask:

- Can this three-Pokemon lineup cover the top-threat pool?
- Which threats have no answer?
- Which threats have exactly one answer?
- Does a single bad lead force the only answer onto the field?
- Are top threats covered across realistic shield paths?

Coverage should reward redundancy without overstacking. Two answers to a key threat are valuable; four answers to a niche threat may be wasted if other threats are uncovered.

Coverage diagnostics should report top-threat and full-meta misses separately. Exporters should render the use-case payload and must not rebuild threat pools or recompute answer counts from raw CSV files.
