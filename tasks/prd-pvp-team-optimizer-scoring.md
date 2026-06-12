# PRD: PvP Team Optimizer Scoring

## Introduction

Improve the Python CLI team generator so it produces stronger, more PvP-informed bring-6 Pokemon GO PvP teams while preserving the existing CLI workflow, supported metas, repository boundaries, and output formats. The optimizer should prioritize full-team quality across coverage, safety, consistency, bulk, role balance, and threat exposure. Existing pick-3 lineup diagnostics should remain available, but full bring-6 quality should become the primary selection objective.

The implementation should adapt PvPoke ranking and Team Builder concepts into maintainable Python logic. It must not execute PvPoke tooling, import PvPoke JavaScript, or depend on runtime vendor JavaScript.

## Goals

- Generate a deterministic best team of 6 for supported metas using rankings, Pokemon data, move data, type data, and shield-scenario simulation matrices.
- Require candidate Pokemon to have an active `overall` PvPoke ranking before they can be selected.
- Filter out candidate Pokemon rows that have missing matchup data in any loaded shield scenario.
- Exclude unranked matchup target columns from ranked threat pools and threat scoring.
- Add full-team A-F grades for coverage, bulk, safety, and consistency with no plus/minus modifiers.
- Add a lower-is-better Threat Score that uses soft matchup quality, top-meta weighting, full-meta breadth, shield stability, no-answer penalties, and single-answer penalties.
- Preserve existing pick-3 lineup diagnostics and output sections where they currently exist.
- Keep all caching in memory and deterministic for a single CLI run.

## User Stories

### US-001: Parse Simulation Matrices Safely
**Description:** As a CLI user, I want simulation CSVs parsed by matchup columns rather than fragile column positions so exported PvPoke summaries do not corrupt optimizer inputs.

**Acceptance Criteria:**
- [ ] Simulation CSV parsing ignores summary columns by header name, including `Wins`, `Losses`, `Draws`, and `Average`.
- [ ] All configured 0-, 1-, and 2-shield files must have matching row labels after filtering.
- [ ] All configured 0-, 1-, and 2-shield files must have matching matchup column labels after excluding summary columns.
- [ ] Blank or non-numeric matchup cells are treated as missing matchup data.
- [ ] Any candidate row with missing matchup data in any loaded shield scenario is excluded before optimization.
- [ ] If fewer than six candidate rows remain, the run fails clearly with the eligible count and reason.
- [ ] Unit tests cover summary-column detection and missing-cell filtering.
- [ ] Typecheck passes.
- [ ] Tests pass.

### US-002: Enforce Ranked Candidate Eligibility
**Description:** As a CLI user, I want only ranked Pokemon to be eligible for team selection so the optimizer does not recommend unsupported or stale candidates.

**Acceptance Criteria:**
- [ ] A candidate Pokemon row must have a normalized species match in the active `overall` ranking profile to be eligible.
- [ ] Candidate species normalization remains deterministic and compatible with existing row labels, move suffixes, IV suffixes, and shadow/base species handling.
- [ ] Unranked candidate rows are filtered out before optimization.
- [ ] If fewer than six ranked candidates remain, the run fails clearly with the eligible count and reason.
- [ ] The ranking eligibility check does not require all role categories for candidate eligibility unless existing meta config explicitly requires those files.
- [ ] Unit tests cover ranked and unranked candidate filtering.
- [ ] Typecheck passes.
- [ ] Tests pass.

### US-003: Build Ranked Threat Pools
**Description:** As a CLI user, I want top-meta and broad-meta threats based on ranked simulation targets so the team is evaluated against realistic opponents.

**Acceptance Criteria:**
- [ ] Top-meta threats are derived from active `overall` rankings intersected with simulation target columns.
- [ ] Full-meta or broad-meta threats are derived from configured `full_meta_ranking_paths` when present and intersected with simulation target columns.
- [ ] Unranked simulation target columns are excluded from threat pools and threat scoring.
- [ ] Threat-pool ordering is deterministic for duplicate forms, missing scores, tied scores, and normalized base species.
- [ ] Top-meta threats carry more scoring weight than broad-meta threats.
- [ ] Unit tests cover top-meta weighting and unranked target exclusion.
- [ ] Typecheck passes.
- [ ] Tests pass.

### US-004: Score Soft Matchup Quality Across Shields
**Description:** As a CLI user, I want matchup strength to affect team quality beyond binary win/loss thresholds so close losses, playable matchups, and hard losses are valued differently.

**Acceptance Criteria:**
- [ ] Combined matchup score uses all available shield scenarios with weights `0.30` for 0-shield, `0.50` for 1-shield, and `0.20` for 2-shield.
- [ ] Soft matchup scoring distinguishes strong answers, playable answers, neutral matchups, soft losses, and hard losses.
- [ ] A hard loss contributes more threat risk than a marginal loss.
- [ ] A team with multiple playable answers scores better than a team with one volatile answer.
- [ ] Shield-stable Pokemon score better than Pokemon that rely on one isolated favorable shield scenario and collapse in others.
- [ ] Unit tests cover shield aggregation, soft matchup differences, and shield stability.
- [ ] Typecheck passes.
- [ ] Tests pass.

### US-005: Add Full-Team Grades And Threat Score
**Description:** As a CLI user, I want concise full-team diagnostics so I can understand why the recommended team is strong or risky.

**Acceptance Criteria:**
- [ ] The result payload includes `coverage_grade`, `bulk_grade`, `safety_grade`, and `consistency_grade` for the recommended team.
- [ ] Grades are limited to `A`, `B`, `C`, `D`, and `F` with no plus/minus variants.
- [ ] The result payload includes lower-is-better `threat_score`.
- [ ] Threat Score penalizes no-answer threats, single-answer threats, hard losses, and severe single-point weaknesses.
- [ ] Threat Score rewards redundant answers, broad playable matchups, and shield-stable coverage.
- [ ] Top-meta risk contributes more to Threat Score than broad-meta long-tail risk.
- [ ] Unit tests cover grade mapping and Threat Score ordering for obviously good and bad fixture teams.
- [ ] Typecheck passes.
- [ ] Tests pass.

### US-006: Prioritize Full Bring-6 Objective In Optimization
**Description:** As a CLI user, I want the selected team to be the strongest full bring-6 roster rather than the roster with the best pick-3 lineup objective.

**Acceptance Criteria:**
- [ ] `TeamOptimizer` keeps existing legality checks and Battle Frontier point rules.
- [ ] Full-team objective and ranking-aware roster quality are considered before pick-3 lineup objective in optimizer comparison.
- [ ] Existing pick-3 lineup diagnostics remain computed and exported where currently supported.
- [ ] Existing score tuple indexes used by exporters and tests are preserved where practical; new fields are appended when additional metrics are needed.
- [ ] Optimizer output remains deterministic for the same inputs and seed.
- [ ] Unit tests cover cases where full bring-6 quality should beat a stronger pick-3 lineup objective.
- [ ] Typecheck passes.
- [ ] Tests pass.

### US-007: Render Improved CLI Diagnostics
**Description:** As a CLI user, I want text and Markdown output to show the key full-team diagnostics without losing existing lineup information.

**Acceptance Criteria:**
- [ ] Text output shows the recommended bring-6 roster, coverage grade, bulk grade, safety grade, consistency grade, and Threat Score.
- [ ] Markdown output shows the same full-team diagnostics.
- [ ] Output distinguishes major top-meta threats from major broad-meta threats when both are available.
- [ ] Existing recommended lineup sections remain present when lineups are produced.
- [ ] Exporters render structured result payload fields and do not recompute scoring logic.
- [ ] Unit tests cover text and Markdown rendering of new metrics.
- [ ] Typecheck passes.
- [ ] Tests pass.

### US-008: Document Assumptions And Tuning Boundaries
**Description:** As a maintainer, I want the scoring assumptions documented so future changes can tune the algorithm without violating architecture boundaries.

**Acceptance Criteria:**
- [ ] Documentation states that PvPoke rankings and simulations are calibration inputs, not runtime tooling.
- [ ] Documentation explains candidate eligibility, missing-matchup filtering, top-meta weighting, full-meta weighting, shield aggregation, and grade mapping.
- [ ] Documentation states that scoring weights and thresholds are internal implementation details and not CLI options.
- [ ] Documentation notes that pick-3 lineups remain diagnostics but full bring-6 quality is the primary selection objective.
- [ ] Typecheck passes.
- [ ] Tests pass, if documentation changes affect tested examples.

## Functional Requirements

- FR-1: The CLI must continue accepting existing supported metas, including Great League, Ultra League, Master League, and NAIC Cup where configured.
- FR-2: The system must load simulation matrices through infrastructure repositories and keep file I/O outside application scoring logic.
- FR-3: The system must ignore simulation CSV summary columns by recognized names rather than fixed trailing-column position.
- FR-4: The system must treat blank or non-numeric matchup cells as missing matchup data.
- FR-5: The system must filter out any candidate Pokemon row with missing matchup data in any configured shield scenario.
- FR-6: The system must fail clearly if fewer than six eligible candidates remain after filtering.
- FR-7: The system must require active `overall` ranking presence for candidate Pokemon eligibility.
- FR-8: The system must exclude unranked simulation target columns from ranked threat pools and threat scoring.
- FR-9: The system must load active ranking paths from `MetaConfig.ranking_paths` and broad/full-meta ranking paths from `MetaConfig.full_meta_ranking_paths` when configured.
- FR-10: The system must normalize Pokemon names deterministically across rankings, simulation rows/columns, Pokemon JSON, and move parsing.
- FR-11: The system must aggregate 0-, 1-, and 2-shield matchup ratings with weights `0.30`, `0.50`, and `0.20` respectively unless a future documented scoring change updates these constants.
- FR-12: The system must use soft matchup scoring for optimizer fitness and diagnostics rather than relying only on `score > 500` binary wins.
- FR-13: The system must compute a lower-is-better Threat Score for the recommended team.
- FR-14: The system must compute A-F full-team grades for coverage, bulk, safety, and consistency.
- FR-15: The system must keep grade values limited to `A`, `B`, `C`, `D`, and `F`.
- FR-16: The system must weight top-meta threat risk more heavily than broad-meta threat risk.
- FR-17: The system must penalize no-answer threats, single-answer threats, hard losses, and severe single-point weaknesses.
- FR-18: The system must reward redundant answers, broad playable matchups, and shield-stable matchups.
- FR-19: The system must preserve existing pick-3 lineup diagnostics and output sections where currently supported.
- FR-20: The optimizer comparison must prioritize full bring-6 quality before pick-3 lineup objective.
- FR-21: The optimizer must remain deterministic for fixed inputs, seed, restart count, worker count, and configuration.
- FR-22: The system must use in-memory caching only.
- FR-23: Exporters must render score and diagnostic fields from the result payload without recomputing application scoring.
- FR-24: New scoring behavior must be covered by unit tests using compact synthetic fixtures rather than large production ranking files where practical.

## Non-Goals

- Do not execute PvPoke tooling.
- Do not import, vendor, or execute PvPoke JavaScript.
- Do not add scoring weights or thresholds as CLI options.
- Do not return multiple alternative teams; return only the best team.
- Do not remove existing pick-3 lineup diagnostics or output sections unless a future task explicitly requests it.
- Do not optimize blind-3 battle order as the primary objective.
- Do not hardcode behavior to one league or cup.
- Do not introduce persistent caches or on-disk cache files.
- Do not calibrate against real-trainer historical teams because no such dataset currently exists.

## Design Considerations

- Human-readable reports should focus on Recommended Bring-6 Roster, Team Analysis, Recommended Lineups, actionable warnings, and Potential Threats.
- Full-team diagnostics should be concise: four letter grades and one numeric lower-is-better Threat Score.
- Major threats should be split between top-meta and broad-meta when the data supports both pools.
- Existing exporter formatting can change where tests allow, but output should remain easy to scan in terminal and Markdown.

## Technical Considerations

- Preserve existing architectural layers: infrastructure repositories load raw data, application modules normalize and score data, use case assembles payloads, CLI validates and wires dependencies, exporters render only.
- `TeamOptimizer._score_team()` already has per-instance caching by sorted team identity; preserve and extend this pattern for new full-team score inputs.
- Precompute per-candidate features and combined shield matchups before search to avoid repeated nested calculations.
- Keep score tuple index compatibility where exporters and tests consume existing fields; append new fields for new metrics.
- Update multiprocessing restart batch inputs if new scoring context data is required in worker processes.
- Keep strict mypy compatibility for `src`.
- Use `tests/fixtures/us031_weighted_scoring/` or small synthetic fixtures for deterministic scoring regressions.

## Success Metrics

- Existing CLI commands still complete for supported configured metas when required data files exist.
- Unit tests cover matrix filtering, ranking eligibility, soft matchup scoring, shield aggregation, grade mapping, Threat Score behavior, and deterministic optimizer output.
- The optimizer returns the same recommended team for repeated runs with identical inputs and seed.
- Recommended teams have no unranked candidate members.
- Recommended teams have no members with missing matchup data in loaded shield scenarios.
- Text and Markdown outputs show all required full-team diagnostics.
- `make typecheck`, `make lint`, and `make test` pass.

## Open Questions

- Should future work require additional ranking categories beyond `overall` for eligibility, or keep non-overall categories as scoring inputs only?
- Should broad/full-meta threat scoring include unranked but fully simulated targets in a separate unranked diagnostic-only bucket?
- Should a future calibration dataset of tournament or real-trainer teams adjust weights after this implementation lands?
- Should pick-3 lineup objective eventually be removed entirely from optimizer tie-breaking, or remain as a low-priority tie-breaker?
