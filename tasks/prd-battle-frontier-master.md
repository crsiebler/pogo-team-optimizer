# PRD: Battle Frontier (Master) League Support

## Introduction

Add support for a new meta called `bfmaster` representing the Battle Frontier (Master) league. This meta uses the standard simulation-matrix analysis flow, but team construction must follow special format rules: a six-Pokemon team may spend at most 11 total points, may include at most one 5-point Pokemon, and may include at most one Mega Pokemon.

The current application can load simulation data for a meta and optimize a team using matchup coverage, bulk, and safety. It does not currently support meta-specific team-construction legality rules. This feature adds the Battle Frontier (Master) meta, its cycle-specific point schedule, and optimizer enforcement so that every recommended team is legal for the format.

## Goals

- Add a new CLI-selectable meta named `bfmaster`.
- Load Battle Frontier (Master) simulation data from the existing `bfmaster` CSV files.
- Load Battle Frontier (Master) switch rankings from the existing `cp10000_battlefrontiermaster_switches_rankings.csv` file.
- Load Battle Frontier point values from a checked-in CSV in `data/`.
- Enforce all Battle Frontier team legality rules during optimization.
- Expose point usage and Battle Frontier rule metrics in output data so users can confirm legality.

## User Stories

### US-001: Select Battle Frontier (Master) from the CLI
**Description:** As a CLI user, I want to choose the Battle Frontier (Master) meta so that I can analyze that league without editing code or config manually.

**Acceptance Criteria:**
- [ ] `--meta bfmaster` is accepted by the CLI parser.
- [ ] `bfmaster` resolves to the three simulation files `data/simulations/bfmaster_0-shield.csv`, `data/simulations/bfmaster_1-shield.csv`, and `data/simulations/bfmaster_2-shield.csv`.
- [ ] Missing required Battle Frontier files still raise a clear validation error before execution.
- [ ] Existing metas continue to load without behavior changes.
- [ ] Typecheck passes.

### US-002: Load Battle Frontier point values from data
**Description:** As a developer, I want Battle Frontier point values stored in a CSV file so that the current cycle rules are easy to audit and update.

**Acceptance Criteria:**
- [ ] Add a checked-in CSV file in `data/` containing species-to-points mappings for the current Battle Frontier cycle.
- [ ] The CSV uses species names that match the normalized names produced by `parse_species()`.
- [ ] The system can load point values by species name through an infrastructure repository.
- [ ] Species not present in the point CSV are treated as `0` points for `bfmaster`.
- [ ] Typecheck passes.

### US-003: Enforce Battle Frontier team legality rules during optimization
**Description:** As a user, I want every recommended Battle Frontier team to obey the league rules so that the optimizer never suggests an illegal team.

**Acceptance Criteria:**
- [ ] The optimizer rejects any `bfmaster` candidate team whose total points exceed `11`.
- [ ] The optimizer rejects any `bfmaster` candidate team containing more than one `5`-point Pokemon.
- [ ] The optimizer rejects any `bfmaster` candidate team containing more than one Mega Pokemon.
- [ ] Existing duplicate-base-species prevention still applies.
- [ ] Randomly seeded starting teams for `bfmaster` are legal.
- [ ] Swap-based local search for `bfmaster` preserves legality after each accepted replacement.
- [ ] Existing non-Battle-Frontier metas continue to behave as before.
- [ ] Typecheck passes.

### US-004: Use the correct switch rankings for Battle Frontier (Master)
**Description:** As a user, I want Battle Frontier analysis to use the correct switch rankings file so that safety scoring reflects the selected meta.

**Acceptance Criteria:**
- [ ] `bfmaster` uses `data/rankings/cp10000_battlefrontiermaster_switches_rankings.csv` automatically.
- [ ] The application no longer relies on the Great League default switch rankings file for `bfmaster` unless the user explicitly overrides it.
- [ ] Existing metas continue to support their current switch ranking behavior.
- [ ] Typecheck passes.

### US-005: Show Battle Frontier legality details in results
**Description:** As a user, I want the output to show point usage and constraint summary so that I can verify the team is legal without recalculating it manually.

**Acceptance Criteria:**
- [ ] Result metrics include total points used for the recommended team.
- [ ] Result metrics include the number of 5-point members on the recommended team.
- [ ] Result metrics include the number of Mega members on the recommended team.
- [ ] Result metrics include the Battle Frontier team rule limits used for the analysis.
- [ ] Text and markdown outputs render the new legality metrics clearly.
- [ ] Existing output formats continue to work when the new metrics are present.
- [ ] Typecheck passes.

### US-006: Validate Battle Frontier behavior with tests
**Description:** As a developer, I want automated tests for Battle Frontier rules so that future changes do not break format legality enforcement.

**Acceptance Criteria:**
- [ ] Add unit tests covering point CSV loading.
- [ ] Add unit tests covering optimizer rejection of over-budget teams.
- [ ] Add unit tests covering optimizer rejection of teams with two 5-point Pokemon.
- [ ] Add unit tests covering optimizer rejection of teams with two Mega Pokemon.
- [ ] Add integration coverage showing `bfmaster` produces a legal six-Pokemon team.
- [ ] `make test` passes.
- [ ] `make typecheck` passes.

## Functional Requirements

- FR-1: The system must support a new meta key named `bfmaster`.
- FR-2: The `bfmaster` meta must load matrix files from `data/simulations/bfmaster_0-shield.csv`, `data/simulations/bfmaster_1-shield.csv`, and `data/simulations/bfmaster_2-shield.csv`.
- FR-3: The meta configuration model must support optional per-meta configuration beyond `matrix_files`, including switch rankings path and Battle Frontier rule data.
- FR-4: The system must load Battle Frontier point values from a checked-in CSV file stored in `data/`.
- FR-5: The point CSV must map normalized species names to integer point values.
- FR-6: For `bfmaster`, any species not present in the point CSV must be treated as `0` points.
- FR-7: For `bfmaster`, the system must enforce a maximum total team point cost of `11`.
- FR-8: For `bfmaster`, the system must enforce a maximum of one `5`-point Pokemon per team.
- FR-9: For `bfmaster`, the system must enforce a maximum of one Mega Pokemon per team.
- FR-10: For `bfmaster`, legality checks must be applied when generating initial random teams and when evaluating candidate replacements during optimization.
- FR-11: Existing unique-base-species rules must remain in effect for `bfmaster` and all existing metas.
- FR-12: For `bfmaster`, the system must use `data/rankings/cp10000_battlefrontiermaster_switches_rankings.csv` unless the user explicitly supplies an override path.
- FR-13: The application result must include legality-related metrics for the recommended Battle Frontier team, including total points used, five-point-member count, Mega count, and the active rule limits.
- FR-14: Text and markdown exporters must render the new legality metrics when they are present.
- FR-15: Existing metas that do not define Battle Frontier rules must continue to optimize teams without point-based constraints.
- FR-16: Configuration and repository validation errors must use actionable messages that identify the missing or invalid file or meta field.

## Non-Goals

- No support for editing Battle Frontier point values from the CLI.
- No support for multiple Battle Frontier cycles in the same release.
- No support for generalized arbitrary team-building rule expressions beyond what is needed for this format.
- No UI changes outside existing CLI and exporter outputs.
- No changes to PvPoke export structure unless required for compatibility with existing exporter behavior.

## Design Considerations

- Reuse existing output patterns for metrics rather than inventing a new report section if the current layout can accommodate the added fields clearly.
- Keep Battle Frontier legality details concise and visible in text and markdown output.

## Technical Considerations

- Team legality rules belong in the application optimization flow, not in CLI parsing or exporters.
- File-backed point data belongs in the infrastructure layer behind a repository interface.
- `parse_species()` should remain the normalization baseline for matching simulation labels to point CSV entries.
- The provided Battle Frontier names must be aligned to actual normalized dataset labels. Examples include:
  - `Zamazenta (Crowned Shield)` instead of `Zamazenta (Crowned Sword)`
  - `Zygarde (Complete Forme)` instead of `Zygarde (100% Complete)`
  - `Meloetta (Aria)` instead of `Meloetta (Aria Forme)`
  - `Dialga (Origin)` instead of the typo `Diagla (Origin)`
- The optimizer currently seeds teams randomly and improves them via swap search. Both stages must enforce legality or the search may produce invalid teams.
- Existing metas should not pay a performance penalty beyond minimal legality checks guarded by optional configuration.

## Success Metrics

- Running `PYTHONPATH=src python -m pogo_team_optimizer.cli.main --meta bfmaster --format text` completes successfully with the provided data files.
- The recommended `bfmaster` team always has total points less than or equal to `11`.
- The recommended `bfmaster` team always contains at most one `5`-point Pokemon.
- The recommended `bfmaster` team always contains at most one Mega Pokemon.
- Existing automated tests for non-Battle-Frontier metas continue to pass.

## Open Questions

- Should per-member point values also be shown directly next to each recommended team member, or are aggregate legality metrics sufficient?
- Should future Battle Frontier cycles reuse the same CSV format and config fields, or should cycle metadata be modeled explicitly later?
