# Pokemon GO Show-6 Pick-3 Team Optimization

This document is the main entry point for a project-agnostic Pokemon GO Battle League team optimization strategy. It is intended for AI agents or engineers implementing an optimizer for show-6, pick-3 formats.

<!-- Reference: docs/team-optimization/scoring-model.md -->
<!-- Reference: docs/team-optimization/lineup-structures.md -->
<!-- Reference: docs/team-optimization/coverage-threat-pools.md -->
<!-- Reference: docs/team-optimization/safety-consistency-bulk.md -->
<!-- Reference: docs/team-optimization/type-effectiveness.md -->
<!-- Reference: docs/team-optimization/role-scoring.md -->
<!-- Reference: docs/team-optimization/data-inputs.md -->
<!-- Reference: docs/team-optimization/validation.md -->
<!-- OpenCode skill: .opencode/skills/gbl-optimizer/SKILL.md -->

## Core Idea

In show-6, pick-3 formats, the best roster is not simply the six strongest individual Pokemon. The goal is to build a six-Pokemon roster with strong full bring-6 quality across complementary coverage, safety, consistency, bulk, typing, and roles, while still exposing multiple ordered three-Pokemon lineups as battle plans and diagnostics.

The optimizer should use weighted strategic scores rather than a strict tier list. A concrete implementation may still use comparison-key ordering for validity, legality, safety, bulk, full-team quality, and lower-priority lineup diagnostics. Keep that ordering explicit so future tuning does not hide hard constraints or confuse optimizer objectives with explainability fields.

## Weighted Priority Order

Use this priority order when choosing weights:

1. Synergy
2. Coverage
3. Safety
4. Consistency
5. Bulk
6. Defensive resistances vs weaknesses ratio
7. Offensive effectiveness vs resistance ratio
8. Role

Higher-priority categories should have larger weights, but lower-priority categories still contribute. A lineup with slightly worse coverage can be better if it has much stronger synergy and safety. A roster with strong matchup coverage can still be rejected if it relies on fragile lineups or repeated shared weaknesses.

## Optimization Flow

1. Build a candidate pool from owned rows with complete matchup data and active overall ranking eligibility.
2. Build ranked top-threat and broader full-meta pools from ranking profiles intersected with simulation targets.
3. Generate candidate show-6 rosters.
4. Enumerate ordered pick-3 lineups from each roster.
5. Score each lineup as a playable battle plan.
6. Score the full bring-6 roster with ranking-aware coverage, safety, consistency, bulk, and type/move ratios.
7. Return the best roster and multiple recommended lineups with explanation metrics.

PvPoke rankings and simulation matrices are calibration inputs, not runtime tooling. Treat them as local best-estimate resources, not fixed truth or external services called during optimization. Prefer score-based and category-specific signals over raw rank alone.

## Implementation Boundaries

Keep ranking-aware optimization separated by layer:

- Infrastructure repositories load raw ranking CSVs, Pokemon data, move data, type charts, and matchup matrices.
- Application services normalize PvPoke category scores, build active-meta/top-threat pools and full-meta pools when supplied with a full-meta profile, enumerate and score lineups, and compute weighted roster components.
- The use case assembles the final roster, recommended lineups, score breakdowns, threat diagnostics, role assumptions, and warnings.
- The CLI validates selected meta configuration and wires repositories into the use case.
- Exporters render structured diagnostics without recomputing coverage, role fit, synergy, shared weaknesses, or ranking-aware scores.

Optimizer objectives are the implemented comparison inputs that decide roster ordering. In this project, `TeamOptimizer._comparison_key()` applies safety-floor deficit, safe-member deficit, bulk deficit, ranking-aware full-team score, legacy full-team quality metrics, then pick-3 lineup diagnostics as lower-priority tie-breakers. Explainability diagnostics are report fields that explain those decisions, such as covered threats, no-answer threats, single-answer threats, shared weaknesses, role assumptions, and lineup dependency. Do not tune exporters by adding new scoring logic there; improve application scoring or use-case diagnostics instead.

For ordered lineups, use one of these models depending on project requirements:

- Lead ordered, back pair unordered: `6 * C(5, 2) = 60` lineups.
- Lead, switch, and closer all ordered: `6P3 = 120` lineups.

If a project has enough role data, fully ordered lead/switch/closer scoring is preferred because switch and closer are different tactical jobs.

## Key Documents

- [Scoring Model](team-optimization/scoring-model.md): weighted objective design and normalization.
- [Lineup Structures](team-optimization/lineup-structures.md): ABC, ABB, and ABA concepts.
- [Coverage And Threat Pools](team-optimization/coverage-threat-pools.md): top-threat and full-meta coverage.
- [Safety, Consistency, And Bulk](team-optimization/safety-consistency-bulk.md): hard-loss, bait-dependence, and bulk scoring.
- [Type Effectiveness](team-optimization/type-effectiveness.md): Pokemon GO multipliers, dual-type calculation, and offensive/defensive ratios.
- [Role Scoring](team-optimization/role-scoring.md): lead, switch, closer, charger, attacker, and consistency ranking use.
- [Data Inputs](team-optimization/data-inputs.md): recommended PvPoke exports and normalized inputs.
- [Validation](team-optimization/validation.md): regression fixtures and expected edge cases.
- OpenCode skill `gbl-optimizer`: project skill for agents implementing, refactoring, or reviewing GBL optimizer logic.

## OpenCode Skill

This strategy is also packaged as the project OpenCode skill `gbl-optimizer` at `.opencode/skills/gbl-optimizer/SKILL.md`.

Use the skill when changing optimizer scoring, show-6 pick-3 lineups, PvPoke ranking inputs, type effectiveness, coverage, safety, consistency, bulk, roles, or ABC/ABB/ABA strategy.

## Output Guidance

Recommended output should explain both roster-level and lineup-level tradeoffs:

- Recommended show-6 roster.
- Overall score and category breakdown.
- Top-threat coverage.
- Full-meta coverage.
- Defensive type profile.
- Offensive move profile.
- Shared weaknesses and single-answer risks.
- Recommended ordered pick-3 lineups.
- ABC, ABB, or ABA structure notes.
- Lead, switch, and closer role notes.
- Major risks and alternative candidates.

The explanation is important. A high aggregate score should not hide a major weakness such as ABA shared weakness into a common top-threat lead.

Human-readable output should stay focused on the recommended bring-6 roster, team analysis, recommended lineups, actionable warnings, and potential threats. Do not reintroduce standalone Safe Cores, full-roster Coverage, or Resource / Shield Safety sections as normal report sections; ordered pick-3 lineup diagnostics are the battle interpretation surface.

Scoring weights, thresholds, shield aggregation values, grade cutoffs, and threat-risk formulas are internal implementation details. They should be documented for maintainers and covered by regression tests, but they are not CLI options unless a future story explicitly adds configuration support.
