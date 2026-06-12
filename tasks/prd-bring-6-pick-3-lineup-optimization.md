# PRD: Bring-6 Pick-3 Lineup Optimization

## Introduction

Update the team optimizer so bring-6-pick-3 formats are evaluated by the ordered three-Pokemon lineups that can actually be brought to battle. The current optimizer scores a six-Pokemon roster as if all six Pokemon can answer every matchup simultaneously, which overvalues paper coverage and can recommend bench Pokemon that are rarely or never strategically bringable.

The new optimizer should evaluate each candidate six-Pokemon roster through its 60 relevant ordered pick-3 lineups: one lead choice and an unordered pair of two back Pokemon. It should also model shield scenarios as resource paths, because shield use by the lead affects the shield state needed from the back pair.

## Goals

- Optimize six-Pokemon rosters using ordered pick-3 lineup quality instead of full-roster best-answer coverage.
- Evaluate all 60 relevant lineups for each six-Pokemon roster: `6 leads * C(5, 2) back pairs`.
- Treat the lead as order-sensitive and the two back Pokemon as an unordered pair.
- Score lineups using fixed shield/resource paths for the first implementation.
- Rank rosters using a weighted combination of top-lineup strength, top-N lineup depth, and viable lineup count.
- Preserve Battle Frontier roster legality while adding point-usage diagnostics for playable lineups.
- Report multiple recommended lineups and actionable threats or warnings without rendering low-value diagnostics by default.
- Keep implementation within the existing architecture boundaries.

## User Stories

### US-001: Enumerate Ordered Pick-3 Lineups
**Description:** As a team optimizer user, I want the system to evaluate each possible lead and back-pair choice so that roster scoring reflects the actual bring-6-pick-3 battle format.

**Acceptance Criteria:**
- [ ] A six-Pokemon roster produces exactly 60 ordered lineups.
- [ ] Each ordered lineup has one lead and two distinct back Pokemon.
- [ ] Back-pair order is canonicalized so `Lead A + B/C` and `Lead A + C/B` are treated as the same lineup.
- [ ] Lead order remains distinct so `Lead A + B/C` and `Lead B + A/C` are different lineups.
- [ ] Unit tests cover lineup enumeration, uniqueness, and canonical ordering.
- [ ] Typecheck/lint passes.

### US-002: Score Ordered Lineups With Resource Paths
**Description:** As a competitive player, I want shield scenarios evaluated as connected resource paths so that a lead that spends shields is paired with backs that can function without shields.

**Acceptance Criteria:**
- [ ] Each ordered lineup is evaluated using fixed resource paths: balanced, shield-spend, and shield-save.
- [ ] Balanced path evaluates lead in 1-shield and backs in 1-shield.
- [ ] Shield-spend path evaluates lead in 2-shield and backs in 0-shield.
- [ ] Shield-save path evaluates lead in 0-shield and backs in 2-shield.
- [ ] Back-pair score for a shield state uses the better matchup result from either back Pokemon.
- [ ] Lineup metrics count dominating matchups where the best available score is greater than `600`.
- [ ] Lineup metrics count overwhelming losses where the best available score is less than `400`.
- [ ] Lineup scoring penalizes weak 0-shield back-pair coverage when the lead relies on 2-shield performance.
- [ ] Unit tests cover a case where a strong 2-shield lead with weak 0-shield backs ranks below a more resource-balanced lineup.
- [ ] Typecheck/lint passes.

### US-003: Score Rosters From Lineup Strength And Depth
**Description:** As a team optimizer user, I want a six-Pokemon roster ranked by its best playable lineups and useful alternatives so that the recommendation is not one strong trio plus three dead roster slots.

**Acceptance Criteria:**
- [ ] Roster comparison uses a weighted combination of best lineup strength, top-N lineup quality, and viable lineup count.
- [ ] The optimizer no longer compares candidate six-Pokemon rosters using full-roster best-answer scoring as the primary objective.
- [ ] Roster scoring avoids averaging all 60 lineups equally as the primary objective.
- [ ] Roster scoring avoids optimizing only the single best lineup as the primary objective.
- [ ] Unit tests cover a case where a roster with better full-six paper coverage loses to a roster with stronger ordered pick-3 lineups.
- [ ] Unit tests cover a case where one excellent lineup plus weak alternatives loses to a roster with comparable top-lineup strength and better depth.
- [ ] Typecheck/lint passes.

### US-004: Rank And Report Multiple Recommended Lineups
**Description:** As a player, I want to see several strong pick-3 options so that I can vary my lineups across a multi-battle match and avoid becoming predictable.

**Acceptance Criteria:**
- [ ] Output includes multiple recommended ordered lineups with lead and back pair.
- [ ] Output does not frame a single lineup as the only default or mandatory choice.
- [ ] Recommended lineups are ranked by lineup score and should include enough viable alternatives for a typical three-battle match when available.
- [ ] Each reported lineup includes shield/resource safety metrics.
- [ ] Existing safe-core reporting is replaced or supplemented by ordered lineup reporting.
- [ ] JSON output includes structured fields for recommended lineups.
- [ ] Text and Markdown exporters render readable lineup sections.
- [ ] Tests cover output shape for at least JSON and one human-readable exporter.
- [ ] Typecheck/lint passes.

### US-005: Report Bench Utility And Unbringable Pokemon
**Description:** As a player, I want to know whether each roster member is actually useful in viable pick-3 lineups so that I can identify paper-coverage picks and weak bench slots.

**Acceptance Criteria:**
- [ ] Each roster member has usage metrics across viable lineups.
- [ ] Bench utility identifies whether a Pokemon is core, flexible, specialist, low utility, or unbringable.
- [ ] Output warns when a roster member appears in few or no viable lineups.
- [ ] Output warns when an expensive Battle Frontier Pokemon is mostly a bench-only member.
- [ ] Output warns when a free or low-point Battle Frontier Pokemon improves paper coverage but is rarely bringable.
- [ ] Tests cover utility classification and warning generation.
- [ ] Typecheck/lint passes.

### US-006: Add Battle Frontier Lineup Diagnostics
**Description:** As a Battle Frontier player, I want point usage explained for the recommended lineups so that I can tell whether points are concentrated in playable Pokemon or wasted on the bench.

**Acceptance Criteria:**
- [ ] Battle Frontier legality remains enforced at the six-roster level.
- [ ] The optimizer does not enforce separate point legality on individual pick-3 lineups in the MVP.
- [ ] Output includes roster points used and points used by each recommended lineup.
- [ ] Output includes free/low-point Pokemon usage rate across viable lineups.
- [ ] Output includes high-point Pokemon usage rate across viable lineups.
- [ ] Tests confirm existing Battle Frontier roster legality constraints still apply.
- [ ] Typecheck/lint passes.

### US-007: Report ABC/ABB/ABA Lineup Labels
**Description:** As a competitive player, I want each ordered lineup labeled by team shape so that I can interpret whether it behaves like ABC, ABB, or ABA.

**Acceptance Criteria:**
- [ ] Recommended lineups include a team-shape label when it can be classified.
- [ ] ABC/ABB/ABA labels are diagnostic only in the MVP and do not directly affect optimization scoring.
- [ ] Documentation explains that classification is heuristic and used for interpretation.
- [ ] Tests cover the output field presence without requiring perfect strategic classification.
- [ ] Typecheck/lint passes.

## Follow-Up Optimization And Output Cleanup

Initial lineup-aware optimization exposed additional requirements from real meta runs. The optimizer now needs to preserve playable lineup quality while avoiding extremely frail rosters, reduce runtime from repeated lineup scoring, and simplify human-readable reports so the output focuses on actionable team choices.

The follow-up work should:

- Preserve bulk viability when lineup-aware scoring finds high-coverage but impractically frail teams.
- Remove noisy normal-output diagnostics that do not help team selection.
- Replace obsolete safe-core terminology with ordered lineup terminology.
- Keep expensive or low-value diagnostics out of normal execution unless they produce actionable warnings or are explicitly requested.
- Add optional process-based parallelism over independent optimizer restarts.
- Keep CLI wiring, application scoring, and exporter presentation responsibilities separated.

### Follow-Up US-012: Preserve Bulk Viability In Lineup-Aware Scoring
**Description:** As a team optimizer user, I want lineup-aware recommendations to preserve minimum team bulk so that strong coverage does not produce unusably frail rosters.

**Acceptance Criteria:**
- [ ] Optimizer comparison penalizes teams below a meta-relative bulk floor before lineup objective.
- [ ] Bulk floor is derived from the loaded candidate pool and exposed or documented clearly enough for maintainers to understand the threshold.
- [ ] Teams at or above the bulk floor continue to compete primarily on lineup quality.
- [ ] Tests prove a below-floor frail high-lineup team loses to a viable bulkier alternative.
- [ ] Typecheck/lint passes.

### Follow-Up US-013: Cache Repeated Lineup And Team Scoring
**Description:** As a CLI user, I want lineup-aware optimization to complete faster by avoiding repeated scoring of identical teams and lineups.

**Acceptance Criteria:**
- [ ] Team score tuples are cached by canonical team identity.
- [ ] Ordered lineup mean scores are cached by ordered lineup identity.
- [ ] Caching preserves deterministic optimizer output for the same seed.
- [ ] Focused optimizer tests pass.
- [ ] Typecheck/lint passes.

### Follow-Up US-014: Simplify Human-Readable Reports
**Description:** As a report reader, I want text and Markdown output to focus on recommended lineups and threats so noisy diagnostics do not obscure the recommendation.

**Acceptance Criteria:**
- [ ] Text output omits `Bench Utility` when there are no actionable warnings.
- [ ] Text output omits standalone `Resource / Shield Safety`.
- [ ] Text output omits legacy `Coverage`.
- [ ] Text output omits `Safe Cores`.
- [ ] Markdown output follows the same simplified section policy.
- [ ] Recommended lineups include concise inline resource summaries when useful.
- [ ] Potential threats remain visible.
- [ ] Exporter tests cover removed and retained sections.
- [ ] Typecheck/lint passes.

### Follow-Up US-015: Replace Top Cores With Top Lineups
**Description:** As a CLI user, I want to control the number of recommended ordered lineups instead of obsolete safe cores.

**Acceptance Criteria:**
- [ ] CLI accepts `--top-lineups` with a default of `5`.
- [ ] `--top-lineups` rejects values greater than `10`.
- [ ] Makefile run targets use `--top-lineups` instead of `--top-cores`.
- [ ] `AnalyzeMetaUseCase` uses the value to limit `recommended_lineups`.
- [ ] Safe-core ranking is not computed for normal report output.
- [ ] CLI tests cover valid, capped, and invalid `--top-lineups` behavior.
- [ ] Typecheck/lint passes.

### Follow-Up US-016: Gate Or Remove Low-Value Bench Utility Work
**Description:** As a CLI user, I want the optimizer to skip non-actionable bench utility diagnostics so report generation is cleaner and avoids unnecessary work.

**Acceptance Criteria:**
- [ ] Normal execution does not compute or render all-core bench utility rows when they provide no actionable warning.
- [ ] Bench warning logic is retained only where actionable warnings are still required.
- [ ] Text and Markdown reports do not render non-warning `Bench Utility` sections.
- [ ] JSON, CSV, and Excel schema changes are documented or tests are intentionally updated.
- [ ] Tests verify no `Bench Utility` section appears when all members are core.
- [ ] Typecheck/lint passes.

### Follow-Up US-017: Add Multiprocessing Restart Batching
**Description:** As a user with a multi-core CPU, I want optimizer restarts to run in separate processes so large metas complete faster.

**Acceptance Criteria:**
- [ ] CLI accepts `--workers` with a default of `1`.
- [ ] Makefile exposes a `WORKERS` variable and passes it to the CLI.
- [ ] `workers=1` uses the existing single-process path.
- [ ] `workers>1` splits restarts into deterministic process batches.
- [ ] Each worker uses a deterministic seed derived from the base seed and worker index.
- [ ] The parent process selects the global best solution using the same comparison key as the single-process path.
- [ ] Tests verify `workers=1` remains deterministic.
- [ ] Tests verify `workers=2` returns a legal deterministic result for fixed inputs.
- [ ] Typecheck/lint passes.

### Follow-Up US-018: Document Performance And Output Controls
**Description:** As a contributor and CLI user, I want documentation for `--top-lineups`, diagnostics, workers, Conda Makefile usage, and simplified output semantics.

**Acceptance Criteria:**
- [ ] README documents `--top-lineups` and its maximum of `10`.
- [ ] README documents Makefile `WORKERS` and `DIAGNOSTICS` variables.
- [ ] README explains that multiprocessing uses processes over restart batches.
- [ ] README explains omitted human-readable sections and where structured diagnostics remain if retained.
- [ ] AGENTS.md records that Safe Cores and full-roster Coverage should not be reintroduced into normal text output.
- [ ] AGENTS.md records that process-based parallelism is preferred over threads for CPU-bound optimizer work.
- [ ] Typecheck/lint passes.

### Follow-Up US-019: Run Final Performance And Regression Gate
**Description:** As a maintainer, I want final validation that output cleanup and performance changes preserve optimizer correctness.

**Acceptance Criteria:**
- [ ] `make lint` passes.
- [ ] `make typecheck` passes.
- [ ] `make test` passes.
- [ ] `make run META=great` completes successfully.
- [ ] `make run META=bfmaster` completes successfully.
- [ ] `make run META=great WORKERS=2` completes successfully if workers are implemented.
- [ ] Text output contains `Recommended Lineups` and `Potential Threats`.
- [ ] Text output does not contain `Safe Cores`, `Coverage`, or non-warning `Bench Utility`.
- [ ] Battle Frontier legality remains enforced.
- [ ] Deterministic optimizer tests still pass.

## Weighted GBL Optimizer Refactor

The next refactor should replace the remaining ad hoc and tuple-priority scoring behavior with a weighted Pokemon GO Battle League optimizer guided by `docs/pokemon-go-team-optimization.md` and the `gbl-optimizer` OpenCode skill.

The goal is to produce bring-6 rosters that maximize trainer skill expression: multiple strong ordered pick-3 lineups, flexible game plans, explainable tradeoffs, and practical coverage into the active meta. The optimizer should use complete PvPoke ranking inputs for active metas: `overall`, `leads`, `switches`, `closers`, `attackers`, `chargers`, and `consistency`. Crucible is outdated and should be removed entirely from supported metas.

Weighted scoring priority:

1. Synergy
2. Coverage
3. Safety
4. Consistency
5. Bulk
6. Defensive resistances vs weaknesses ratio
7. Offensive effectiveness vs resistance ratio
8. Role

Hard filters should remain limited to validity and legality constraints, such as duplicate base species, roster size, league eligibility, and Battle Frontier point rules. Strategic quality should be modeled as normalized weighted score components, not a strict tier list.

### Follow-Up US-020: Remove Crucible Meta Support
**Description:** As a maintainer, I want Crucible-specific meta configuration and fixtures removed so the optimizer focuses on current supported GBL metas.

**Acceptance Criteria:**
- [x] `crucible` is removed from `data/metas.json`.
- [x] `crucible` is removed from CLI-supported meta choices.
- [x] CLI rejects `--meta crucible` with an actionable error.
- [x] Crucible-specific docs, tests, and examples are removed or archived as historical data only.
- [x] Tests that assumed Crucible availability are updated.
- [x] Focused tests pass.
- [x] Typecheck passes.

### Follow-Up US-021: Add Generic PvPoke Ranking Category Models And Repository
**Description:** As the optimizer, I need a generic ranking repository that loads PvPoke category rankings for `overall`, `leads`, `switches`, `closers`, `attackers`, `chargers`, and `consistency` so scoring can use role-specific category strength instead of only switch scores.

**Acceptance Criteria:**
- [x] Add a typed ranking category model for all supported PvPoke categories.
- [x] Add immutable ranking row/profile structures for raw and normalized category scores.
- [x] Add or replace repository interfaces so category ranking access is generic rather than switch-only.
- [x] CSV repository loads PvPoke `Pokemon,Score` rows for all configured categories.
- [x] Repository normalizes species names using existing normalization helpers.
- [x] Missing species or category scores are handled by application-level policy, not infrastructure defaults.
- [x] Existing switch-ranking behavior remains covered by compatibility tests or explicit migration tests.
- [x] Focused tests pass.
- [x] Typecheck passes.

### Follow-Up US-022: Extend Meta Config With Ranking Paths For Active Metas
**Description:** As a maintainer, I want active metas to declare all available PvPoke category ranking CSV paths so ranking-aware optimization is configured explicitly and validated before execution.

**Acceptance Criteria:**
- [ ] `MetaConfig` supports a typed `ranking_paths` mapping by category.
- [ ] Active metas declare available ranking paths for `overall`, `leads`, `switches`, `closers`, `attackers`, `chargers`, and `consistency`.
- [ ] Full-meta ranking paths can be associated with active metas for broad coverage pools.
- [ ] Config loading rejects unsupported ranking category keys.
- [ ] Missing configured ranking files are detected before repository construction.
- [ ] Legacy `switch_rankings_path` behavior is migrated or explicitly deprecated.
- [ ] CLI remains validation and wiring only.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

### Follow-Up US-023: Build Top-Threat And Full-Meta Scoring Pools
**Description:** As the optimizer, I need explicit threat pools built from active-meta and full-meta ranking inputs so roster scoring can evaluate both practical top threats and broad meta robustness.

**Acceptance Criteria:**
- [ ] Add an application-level pool builder that consumes ranking profiles and matrix labels.
- [ ] Builder produces an active-meta pool, a full-meta pool, and a weighted top-threat pool.
- [ ] Top-threat pool is derived primarily from configured `overall` rankings and matrix-aligned labels.
- [ ] Pool builder aligns ranking species to matrix row/column labels using existing normalization.
- [ ] Duplicate forms and base species are handled deterministically according to optimizer uniqueness rules.
- [ ] Missing ranking entries use deterministic fallback behavior and do not crash analysis.
- [ ] Tests cover label alignment, missing species, duplicate normalized names, and deterministic ordering.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

### Follow-Up US-024: Add Weighted Score Structures For Ranking-Aware Optimization
**Description:** As a contributor, I want ranking-derived score components represented by explicit structures so optimizer weighting is readable, testable, and explainable.

**Acceptance Criteria:**
- [ ] Add immutable score structures for weighted components and score breakdowns.
- [ ] Add role-fit, threat-coverage, synergy, safety, consistency, bulk, defensive ratio, offensive ratio, and roster score structures.
- [ ] Score objects expose final numeric score and component diagnostics.
- [ ] Weight values are centralized as named constants or config dataclasses.
- [ ] Existing tuple score consumers are migrated safely or preserved until a dedicated migration story updates them.
- [ ] Infrastructure repository details do not leak into application scoring structures.
- [ ] Tests cover weighted sum calculation, missing component handling, and deterministic component ordering.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

### Follow-Up US-025: Normalize PvPoke Category Scores
**Description:** As the optimizer, I need PvPoke category scores normalized consistently so `overall`, `leads`, `switches`, `closers`, `attackers`, `chargers`, and `consistency` values can be combined without scale accidents.

**Acceptance Criteria:**
- [ ] Add a normalization policy for PvPoke category scores.
- [ ] Policy handles PvPoke scores on the `0` to `100` scale.
- [ ] Policy handles degenerate categories where all scores are equal.
- [ ] Policy handles missing species/category values through explicit defaults.
- [ ] Raw scores remain available for diagnostics.
- [ ] Normalized score range and fallback behavior are documented.
- [ ] Tests cover high/low values, equal-value categories, missing scores, malformed rows, and deterministic output.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

### Follow-Up US-026: Score Ordered Lineups With Role Fit
**Description:** As a competitive player, I want recommended lineups to account for PvPoke role fit so leads are evaluated as leads and backline Pokemon are evaluated by switch, closer, attacker, charger, and consistency utility.

**Acceptance Criteria:**
- [ ] Ordered lineup scoring includes role-fit components in addition to matrix resource-path scores.
- [ ] Lead role fit uses the `leads` ranking category.
- [ ] Back pair role fit uses a deterministic blend of `switches` and `closers`.
- [ ] Secondary role modifiers can use `attackers`, `chargers`, and `consistency`.
- [ ] Role-fit scoring does not reorder an unordered back pair unless a future fully ordered switch/closer model is implemented.
- [ ] Role-fit weights are explicit and test-covered.
- [ ] Existing resource-path matchup scoring remains intact.
- [ ] Tests prove role fit can change ranking between otherwise similar lineups.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

### Follow-Up US-027: Implement Synergy And ABC/ABB/ABA Scoring
**Description:** As a competitive player, I want ABC, ABB, and ABA lineup strategy to contribute to weighted synergy scoring so recommended teams reflect real GBL alignment decisions.

**Acceptance Criteria:**
- [ ] ABC/ABB/ABA shape labels remain explainable diagnostics and also feed tested synergy components.
- [ ] ABC lineups are rewarded for complementary strengths and low shared weakness exposure.
- [ ] Valid ABB lineups are rewarded when the singleton covers the pair's shared weakness or the pair covers the singleton's weakness.
- [ ] Unsafe ABA shared weakness is penalized when the shared weakness can appear in the lead and the B Pokemon is the only reliable answer.
- [ ] ABA shared strength is rewarded when it creates redundant answers to important top threats.
- [ ] Tests cover ABC, intentional ABB, unsafe ABA shared weakness, and beneficial ABA shared strength.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

### Follow-Up US-028: Add Weighted Coverage, Safety, Consistency, Bulk, And Type Ratio Components
**Description:** As a trainer, I want lineup and roster scoring to incorporate practical coverage, safety, consistency, bulk, defensive ratios, and offensive ratios so recommendations maximize all aspects of GBL play.

**Acceptance Criteria:**
- [ ] Coverage scoring separates top-threat coverage from full-meta coverage.
- [ ] Top-threat misses carry higher weight than long-tail full-meta misses.
- [ ] Safety scoring accounts for overwhelming losses, no-answer threats, single-answer threats, safe-swap quality, and shield-path fragility.
- [ ] Consistency scoring uses PvPoke consistency ranking and proxies for bait dependence, move DPE, and shield stability where available.
- [ ] Bulk uses stat product or `defense * hp / attack` fallback and remains normalized to the candidate pool.
- [ ] Defensive ratios use `data/type-effectiveness.json`, dual-type multiplication, and meta-weighted shared weakness exposure.
- [ ] Offensive ratios use selected move types, type effectiveness, and top-threat/full-meta resistance pressure.
- [ ] Tests cover each component and weighted tradeoffs between components.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

### Follow-Up US-029: Preserve Deterministic Performance With Ranking-Aware Scores
**Description:** As a user, I want ranking-aware optimization to remain deterministic and performant when caching and multiprocessing are enabled.

**Acceptance Criteria:**
- [ ] Team score cache keys include all deterministic ranking-aware scoring inputs.
- [ ] Lineup score cache keys account for role-fit or ranking profile identity.
- [ ] Cached scores do not depend on mutable repository instances.
- [ ] Multiprocessing payloads contain picklable dataclasses or plain data only.
- [ ] `workers=1` continues to use the existing single-process path.
- [ ] `workers>1` produces deterministic results for fixed seed, worker count, and input files.
- [ ] Parent process selects the best solution using the same weighted comparison result.
- [ ] Tests cover deterministic results for workers `1` and `2`.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

### Follow-Up US-030: Add Explainable Ranking-Aware Output
**Description:** As a trainer, I want reports to explain why a bring-6 roster and its lineups were selected so I can understand tradeoffs and improve play.

**Acceptance Criteria:**
- [ ] Result payload includes weighted component scores for the recommended roster.
- [ ] Result payload includes weighted component scores for recommended lineups.
- [ ] Output identifies key covered threats, remaining threats, no-answer threats, single-answer threats, shared weaknesses, and role assumptions.
- [ ] Output identifies when a roster is too dependent on one lineup.
- [ ] JSON includes structured ranking-aware diagnostics when available.
- [ ] Text and Markdown summarize only high-value ranking-aware diagnostics without reintroducing noisy legacy sections.
- [ ] CSV and Excel preserve stable schemas or update tests and docs intentionally.
- [ ] Exporters do not compute scores.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

### Follow-Up US-031: Add Deterministic Regression Fixtures For Weighted GBL Scoring
**Description:** As a maintainer, I want small deterministic fixtures for rankings, typing, moves, matrices, and meta pools so future scoring changes do not silently regress strategic quality.

**Acceptance Criteria:**
- [ ] Add minimal ranking CSV fixtures for all PvPoke categories.
- [ ] Fixtures include overlapping species, missing species, duplicate normalized species, tied scores, and category gaps.
- [ ] Tests do not rely on large production ranking CSVs unless explicitly marked integration.
- [ ] Tests cover active-meta ranking profile loading and full-meta/top-threat pool construction.
- [ ] Tests cover weighted score ordering and multiple-lineup roster preference.
- [ ] Tests cover Crucible removal behavior.
- [ ] Optimizer tests use explicit seeds.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

### Follow-Up US-032: Document Ranking-Aware Optimization Architecture
**Description:** As a contributor and future agent, I want documentation explaining category ranking inputs, meta config paths, pool construction, weighted score outputs, explainability metrics, validation, and architecture boundaries.

**Acceptance Criteria:**
- [ ] README documents category ranking CSV inputs and current active meta behavior.
- [ ] README documents that Crucible is no longer supported.
- [ ] `docs/pokemon-go-team-optimization.md` and `docs/team-optimization/` subdocs are updated to match implemented ranking-aware behavior.
- [ ] `.opencode/skills/gbl-optimizer/SKILL.md` is updated with any new implementation obligations.
- [ ] AGENTS.md records that repositories load rankings, application builds pools and scores, CLI wires dependencies only, and exporters render diagnostics only.
- [ ] Documentation explains deterministic testing expectations and multiprocessing/caching implications.
- [ ] Documentation distinguishes optimizer objectives from explainability-only diagnostics.
- [ ] Typecheck passes.

### Follow-Up US-033: Add Local PvPoke CSV Data Sync
**Description:** As a maintainer, I want a Makefile-backed sync workflow that reads from the local `vendor/pvpoke` source tree and reproduces the PvPoke rankings page CSV export so `pokemon.json`, `moves.json`, and flat ranking CSV files stay current without changing the optimizer to read ranking JSON.

**Acceptance Criteria:**
- [ ] `https://github.com/crsiebler/pvpoke` is available as a git submodule at `vendor/pvpoke`.
- [ ] Makefile exposes a sync target, such as `make sync`, that runs the local data synchronization workflow.
- [ ] Sync reads gamemaster inputs from `vendor/pvpoke/src/data/gamemaster/pokemon.json` and `vendor/pvpoke/src/data/gamemaster/moves.json`.
- [ ] Sync uses PvPoke ranking source data only as an intermediate source and does not make ranking JSON a runtime optimizer input.
- [ ] Sync reproduces the PvPoke rankings page `Export to CSV` format from `vendor/pvpoke/src/js/interface/RankingInterface.js`, including the full header: `Pokemon,Score,Dex,Type 1,Type 2,Attack,Defense,Stamina,Stat Product,Level,CP,Fast Move,Charged Move 1,Charged Move 2,Charged Move 1 Count,Charged Move 2 Count,Buddy Distance,Charged Move Cost`.
- [ ] Sync writes deterministic outputs to this repository's `data/pokemon.json`, `data/moves.json`, and flat ranking CSV files under `data/rankings/`.
- [ ] Sync preserves the existing flat ranking filename convention: `data/rankings/cp{cp}_{cup}_{category}_rankings.csv`.
- [ ] Sync supports categories: `overall`, `leads`, `switches`, `closers`, `attackers`, `chargers`, and `consistency`.
- [ ] Sync maps PvPoke cup/category/league paths to the `data/metas.json` ranking paths introduced by ranking-aware meta configuration without requiring nested ranking directories.
- [ ] Sync validates generated rankings page-compatible CSVs before replacing existing files.
- [ ] Sync can skip missing optional ranking files with a clear warning while failing on missing required gamemaster files.
- [ ] Sync does not generate or overwrite simulation matrix CSVs; meta matrices remain manually supplied.
- [ ] README documents submodule setup, `git submodule update --init --recursive`, and the Makefile sync command.
- [ ] Tests cover path mapping, rankings page-compatible CSV generation, missing optional rankings, required gamemaster failures, flat filename preservation, and the no-simulation-sync guarantee.
- [ ] Focused tests pass.
- [ ] Typecheck passes.

## Functional Requirements

- FR-1: The optimizer must enumerate ordered pick-3 lineups for each candidate six-Pokemon roster.
- FR-2: The optimizer must treat lead choice as order-sensitive.
- FR-3: The optimizer must treat the back pair as unordered for lineup identity and scoring.
- FR-4: The optimizer must evaluate exactly 60 ordered lineups for a six-Pokemon roster.
- FR-5: The optimizer must score each ordered lineup using existing 0/1/2 shield matrices.
- FR-6: The optimizer must compute a balanced resource path using lead 1-shield and back-pair 1-shield results.
- FR-7: The optimizer must compute a shield-spend resource path using lead 2-shield and back-pair 0-shield results.
- FR-8: The optimizer must compute a shield-save resource path using lead 0-shield and back-pair 2-shield results.
- FR-9: The optimizer must include a penalty or lower ranking for lineups where lead 2-shield strength is paired with weak 0-shield back-pair coverage.
- FR-10: The optimizer must count dominating matchups where the best available score is greater than `600`.
- FR-11: The optimizer must count overwhelming losses where the best available score is less than `400`.
- FR-12: Dominating and overwhelming counts/rates must be included in lineup metrics and roster-level aggregate metrics.
- FR-13: The optimizer must aggregate ordered lineup scores into a roster score using top-lineup strength, top-N depth, and viable lineup count.
- FR-14: The optimizer must not use full-six best-answer coverage as the primary comparison objective for bring-6-pick-3 optimization.
- FR-15: The optimizer must preserve deterministic behavior for the same seed and input data.
- FR-16: The optimizer must preserve base-species uniqueness rules for roster construction.
- FR-17: Battle Frontier roster legality must continue to cap total roster points, 5-point members, and Mega members.
- FR-18: Battle Frontier lineup point metrics must be reported as diagnostics, not additional legality constraints, in the MVP.
- FR-19: The result model must expose recommended lineups, lineup metrics, warnings, and any retained optional diagnostics.
- FR-20: Exporters must render the new lineup-aware output in text, Markdown, JSON, CSV, and Excel where applicable.
- FR-21: Existing metric names whose meanings change must be renamed or clearly documented to avoid confusion between roster-level and lineup-level metrics.
- FR-22: The CLI must remain a wiring and validation layer and must not contain scoring logic.
- FR-23: File I/O and formatting must remain in infrastructure repositories/exporters.
- FR-24: The optimizer must include a meta-relative bulk viability guard so lineup score cannot select extremely frail rosters when viable bulkier alternatives exist.
- FR-25: The text and Markdown reports must omit `Bench Utility`, standalone `Resource / Shield Safety`, legacy `Coverage`, and `Safe Cores` sections unless a section contains actionable warnings or diagnostics are explicitly requested.
- FR-26: Recommended lineups must include concise inline resource summaries instead of relying on a separate normal-output resource safety section.
- FR-27: The CLI must replace `--top-cores` with `--top-lineups` for normal lineup report sizing.
- FR-28: `--top-lineups` must reject values greater than `10`.
- FR-29: The Makefile must expose `TOP_LINEUPS`, `WORKERS`, and `DIAGNOSTICS` variables for CLI execution.
- FR-30: The optimizer must avoid repeated scoring of identical teams and ordered lineups during local search.
- FR-31: The optimizer should support multiprocessing over independent restart batches when `workers > 1`.
- FR-32: Multiprocessing must remain deterministic for a fixed seed and worker count.
- FR-33: Safe-core computation must not run during normal lineup-focused report generation unless retained explicitly for backward-compatible machine-readable diagnostics.
- FR-34: Bench utility computation must be gated behind actionable warnings or diagnostics when it would otherwise render all roster members as core.
- FR-35: Crucible must be removed from supported active metas and CLI choices because it is outdated and no longer played.
- FR-36: Active metas must be able to declare PvPoke ranking paths for `overall`, `leads`, `switches`, `closers`, `attackers`, `chargers`, and `consistency`.
- FR-37: Ranking-aware scoring must build separate top-threat and full-meta pools.
- FR-38: Normal roster and lineup quality scoring must use weighted normalized components instead of a strict tier-list comparator.
- FR-39: Weighted scoring must preserve the priority order Synergy, Coverage, Safety, Consistency, Bulk, Defensive Ratio, Offensive Ratio, and Role.
- FR-40: Ordered lineup scoring must include role-fit signals from PvPoke category rankings.
- FR-41: Synergy scoring must account for ABC, ABB, ABA, shared weakness, shared strength, and single-answer alignment risk.
- FR-42: Coverage scoring must evaluate top-threat and full-meta coverage separately.
- FR-43: Defensive and offensive type ratio scoring must use `data/type-effectiveness.json` and dual-type multiplication.
- FR-44: Ranking-aware diagnostics must expose score component breakdowns without making exporters responsible for scoring.
- FR-45: A Makefile-backed local sync workflow must update gamemaster JSON and ranking CSV inputs from `vendor/pvpoke` while leaving simulation matrices untouched.

## Non-Goals

- Do not implement configurable resource-path weights in the MVP.
- Do not evaluate every possible shield allocation beyond the three fixed resource paths in the MVP.
- Do not make ABC/ABB/ABA labels the only scoring basis; the weighted refactor may use tested shape-derived synergy components alongside matchup, coverage, safety, and role signals.
- Do not enforce Battle Frontier point legality on individual pick-3 lineups in the MVP.
- Do not add a UI or browser-based workflow.
- Do not modify input matrix file formats.
- Do not add external services or online API calls.
- Do not generate, download, or overwrite simulation matrix CSVs in the local PvPoke sync workflow.
- Do not optimize for move-timing, bait prediction, switch-clock behavior, or human decision-tree simulation in the MVP.
- Do not parallelize individual matchup cells or resource-path calculations in the first multiprocessing pass.
- Do not use Python threads for CPU-bound optimizer scoring.
- Do not keep Safe Cores in normal human-readable output once Recommended Lineups exist.
- Do not render Bench Utility unless it contains actionable warnings or diagnostics are explicitly requested.
- Do not optimize blindly for raw PvPoke rank or Overall score without lineup synergy, coverage, safety, and explainability.
- Do not let role scoring dominate the weighted objective; role is useful but lower-priority than synergy, coverage, safety, consistency, and bulk.

## Design Considerations

The CLI output should distinguish the six-Pokemon roster from the ordered pick-3 lineups.

Recommended human-readable structure after the follow-up cleanup:

```text
Recommended Bring-6 Roster
- ...

Recommended Lineups
- #1 Lead ... | Back Pair ... + ... | Score ... | Resources ...
- #2 Lead ... | Back Pair ... + ... | Score ... | Resources ...
- #3 Lead ... | Back Pair ... + ... | Score ... | Resources ...

Potential Threats
- ...

Warnings
- Unbringable bench members
- Weak single-answer threats
- Battle Frontier point concentration risks
```

Normal text and Markdown reports should not include standalone `Bench Utility`, `Resource / Shield Safety`, `Coverage`, or `Safe Cores` sections. `Bench Utility` may appear only when it contains actionable warnings or when diagnostics are explicitly requested. Resource-path details should be summarized inline with each recommended lineup.

JSON output may change to a cleaner lineup-aware schema. Existing output fields may be renamed or replaced when preserving old names would make metric meaning ambiguous.

Machine-readable outputs may retain compatibility fields temporarily, but the normal report path should not compute obsolete diagnostics solely for human-readable sections.

## Technical Considerations

- Keep ordered lineup and roster scoring in `pogo_team_optimizer.application`.
- `src/pogo_team_optimizer/application/optimizer.py` is the primary impacted module.
- `src/pogo_team_optimizer/application/analyzers.py` may need shared helpers or new analyzers for lineup reporting, bench utility, warnings, and ABC/ABB/ABA labels.
- `src/pogo_team_optimizer/application/use_case.py` must expose the new result structure to exporters.
- Exporters in `src/pogo_team_optimizer/infrastructure/exporters/` must be updated for the new report sections.
- Existing Battle Frontier point loading in `CsvBattleFrontierPointsRepository` should remain unchanged.
- Prefer small application-level dataclasses for ordered lineups and lineup evaluation results.
- Cache lineup or roster scoring if performance degrades due to evaluating 60 lineups per candidate roster.
- Preserve deterministic tie-breaking when lineup scores are equal.
- Use process-based parallelism for CPU-bound optimizer restart batching. Avoid Python threads for optimizer scoring because the workload is CPU-bound pure Python.
- Keep multiprocessing boundaries around independent restart chunks, not individual matchup or resource-path cells.

Potential dataclass concepts:

```python
OrderedLineup
LineupEvaluation
RosterLineupEvaluation
BenchUtility
LineupWarning
```

These names are suggestions, not mandatory implementation requirements.

## Success Metrics

- A six-Pokemon roster is scored from 60 ordered pick-3 lineups instead of full-six best-answer coverage.
- Regression tests demonstrate that paper-coverage bench Pokemon no longer drive roster selection when they are not part of viable lineups.
- Reports identify multiple recommended lineups suitable for varying pick-3 choices across a multi-battle match.
- Reports identify low-utility or unbringable roster members only when those warnings are actionable.
- Battle Frontier output explains point usage in each recommended lineup.
- Normal human-readable reports focus on `Recommended Lineups` and `Potential Threats` instead of legacy coverage or safe-core sections.
- Large metas can use process-based restart batching to reduce wall-clock runtime while preserving deterministic results for fixed seed and worker count.
- `make lint`, `make typecheck`, and `make test` pass.

## Testing Requirements

- Add unit tests for ordered lineup enumeration.
- Add unit tests for lead-sensitive scoring.
- Add unit tests proving back-pair order does not affect score.
- Add unit tests for fixed resource paths.
- Add unit tests for dominating matchup counts using `score > 600`.
- Add unit tests for overwhelming loss counts using `score < 400`.
- Add unit tests for resource-safety penalties.
- Add optimizer regression tests where full-six paper coverage differs from ordered lineup quality.
- Add Battle Frontier regression tests for roster-level legality and lineup point diagnostics.
- Add exporter tests for new JSON and human-readable output sections.
- Add deterministic tests using explicit seeds.
- Add tests for `--top-lineups` validation and Makefile wiring where practical.
- Add tests for simplified text and Markdown output sections.
- Add tests for deterministic `workers=1` and `workers=2` optimizer behavior after multiprocessing is implemented.

Recommended local validation:

```bash
make lint
make typecheck
make test
```

## Rollout Considerations

- This feature intentionally changes optimizer behavior and may change output schemas.
- Release notes should explain that recommendations are now lineup-aware for bring-6-pick-3 formats.
- Existing full-roster metrics should be renamed, removed, or documented as secondary diagnostics to avoid misleading users.
- If CSV/Excel schema changes are substantial, document the new columns in the README or output documentation.
- Consider keeping a short migration note for users comparing older reports to new reports.
- Treat `--top-cores` as obsolete in normal CLI usage and migrate documentation and Makefile examples to `--top-lineups`.
- If machine-readable compatibility fields are retained temporarily, document which fields are legacy diagnostics and avoid rendering them in normal text or Markdown reports.

## Open Questions

- What exact weights should be used for top-lineup strength, top-N depth, and viable lineup count?
- What threshold defines a viable lineup?
- Should machine-readable JSON, CSV, and Excel outputs remove legacy diagnostics at the same time as human-readable output, or retain compatibility fields for one release?
- Should top-N depth use top 3, top 5, top 10, or a weighted blend?
- Should weak single-answer penalties use fixed matchup thresholds such as `501-550`, `551-600`, and `600+` while preserving `>600` as dominating and `<400` as overwhelming?
- Should any metas opt out of lineup-aware optimization, or should this become the default for all metas?
- Should the default worker count remain `1` for deterministic baseline behavior, or automatically use a bounded CPU count when restarts are high?
