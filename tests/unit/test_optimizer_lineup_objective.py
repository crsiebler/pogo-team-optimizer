import pogo_team_optimizer.application.optimizer as optimizer_module
from pogo_team_optimizer.application.lineups import OrderedLineup, score_roster_lineup_depth
from pogo_team_optimizer.application.optimizer import TeamOptimizer


def _optimizer_with_rows(rows: list[list[int]]) -> TeamOptimizer:
    matrices = [rows, rows, rows]
    return TeamOptimizer(
        row_labels=[f"Mon {index}" for index in range(len(rows))],
        col_labels=[f"Opp {index}" for index in range(len(rows[0]))],
        matrices=matrices,
        bulk_by_row=[200.0] * len(rows),
        seed=7,
    )


def _optimizer_with_bulk(rows: list[list[int]], bulk_by_row: list[float]) -> TeamOptimizer:
    matrices = [rows, rows, rows]
    return TeamOptimizer(
        row_labels=[f"Mon {index}" for index in range(len(rows))],
        col_labels=[f"Opp {index}" for index in range(len(rows[0]))],
        matrices=matrices,
        bulk_by_row=bulk_by_row,
        seed=7,
    )


def _comparison_key(optimizer: TeamOptimizer, team: list[int]) -> tuple[float, ...]:
    return optimizer._comparison_key(
        team,
        optimizer._score_team(team),
        safety_floor=None,
        min_safe_members=0,
        safe_member_floor=90.0,
    )


def test_lineup_objective_prefers_stronger_pick_three_over_full_six_paper_coverage() -> None:
    rows = [
        [700, 300, 300, 300, 300, 300],
        [300, 700, 300, 300, 300, 300],
        [300, 300, 700, 300, 300, 300],
        [300, 300, 300, 700, 300, 300],
        [300, 300, 300, 300, 700, 300],
        [300, 300, 300, 300, 300, 700],
        [650, 650, 650, 650, 650, 300],
        [650, 650, 650, 650, 650, 300],
        [650, 650, 650, 650, 650, 300],
        [650, 650, 650, 650, 650, 300],
        [650, 650, 650, 650, 650, 300],
        [650, 650, 650, 650, 650, 300],
    ]
    optimizer = _optimizer_with_rows(rows)
    paper_coverage_team = [0, 1, 2, 3, 4, 5]
    lineup_strength_team = [6, 7, 8, 9, 10, 11]

    assert optimizer._score_team(paper_coverage_team)[1] > optimizer._score_team(
        lineup_strength_team
    )[1]
    assert _comparison_key(optimizer, lineup_strength_team) > _comparison_key(
        optimizer, paper_coverage_team
    )


def test_lineup_objective_prefers_depth_over_one_excellent_lineup() -> None:
    rows = [
        [650, 300, 300, 300],
        [300, 650, 300, 300],
        [300, 300, 650, 650],
        [300, 300, 300, 300],
        [300, 300, 300, 300],
        [300, 300, 300, 300],
        [620, 620, 620, 620],
        [620, 620, 620, 620],
        [620, 620, 620, 620],
        [620, 620, 620, 620],
        [620, 620, 620, 620],
        [620, 620, 620, 620],
    ]
    optimizer = _optimizer_with_rows(rows)
    one_lineup_team = [0, 1, 2, 3, 4, 5]
    depth_team = [6, 7, 8, 9, 10, 11]

    assert optimizer._score_team(one_lineup_team)[14] > optimizer._score_team(depth_team)[14]
    assert _comparison_key(optimizer, depth_team) > _comparison_key(optimizer, one_lineup_team)


def test_comparison_penalizes_below_pool_bulk_before_lineup_objective() -> None:
    rows = [
        [760, 760, 760, 760],
        [760, 760, 760, 760],
        [760, 760, 760, 760],
        [760, 760, 760, 760],
        [760, 760, 760, 760],
        [760, 760, 760, 760],
        [700, 700, 700, 700],
        [700, 700, 700, 700],
        [700, 700, 700, 700],
        [700, 700, 700, 700],
        [700, 700, 700, 700],
        [700, 700, 700, 700],
    ]
    optimizer = _optimizer_with_bulk(
        rows,
        bulk_by_row=[120.0] * 6 + [240.0] * 6,
    )
    frail_high_lineup_team = [0, 1, 2, 3, 4, 5]
    bulky_lower_lineup_team = [6, 7, 8, 9, 10, 11]

    assert optimizer._score_team(frail_high_lineup_team)[13] > optimizer._score_team(
        bulky_lower_lineup_team
    )[13]
    assert _comparison_key(optimizer, bulky_lower_lineup_team) > _comparison_key(
        optimizer, frail_high_lineup_team
    )


def test_bulk_floor_is_derived_from_loaded_candidate_pool() -> None:
    rows = [[600, 600]] * 4
    optimizer = _optimizer_with_bulk(rows, bulk_by_row=[100.0, 150.0, 250.0, 300.0])

    assert optimizer.bulk_floor == 200.0


def test_above_floor_teams_continue_to_compare_by_lineup_objective() -> None:
    rows = [
        [760, 760, 760, 760],
        [760, 760, 760, 760],
        [760, 760, 760, 760],
        [760, 760, 760, 760],
        [760, 760, 760, 760],
        [760, 760, 760, 760],
        [700, 700, 700, 700],
        [700, 700, 700, 700],
        [700, 700, 700, 700],
        [700, 700, 700, 700],
        [700, 700, 700, 700],
        [700, 700, 700, 700],
        [500, 500, 500, 500],
        [500, 500, 500, 500],
        [500, 500, 500, 500],
        [500, 500, 500, 500],
        [500, 500, 500, 500],
        [500, 500, 500, 500],
    ]
    optimizer = _optimizer_with_bulk(
        rows,
        bulk_by_row=[210.0] * 6 + [240.0] * 6 + [100.0] * 6,
    )
    stronger_lineup_team = [0, 1, 2, 3, 4, 5]
    weaker_lineup_team = [6, 7, 8, 9, 10, 11]

    assert optimizer._score_team(stronger_lineup_team)[13] > optimizer._score_team(
        weaker_lineup_team
    )[13]
    assert _comparison_key(optimizer, stronger_lineup_team) > _comparison_key(
        optimizer, weaker_lineup_team
    )


def test_team_score_cache_reuses_canonical_team_identity() -> None:
    rows = [
        [650, 620, 610, 600],
        [610, 650, 620, 600],
        [620, 610, 650, 600],
        [600, 620, 610, 650],
        [640, 640, 610, 610],
        [610, 610, 640, 640],
    ]
    optimizer = _optimizer_with_rows(rows)

    score = optimizer._score_team([0, 1, 2, 3, 4, 5])
    reversed_score = optimizer._score_team([5, 4, 3, 2, 1, 0])

    assert reversed_score == score
    assert len(optimizer._team_score_cache) == 1


def test_lineup_mean_score_cache_canonicalizes_back_pair_only() -> None:
    rows = [
        [650, 620, 610],
        [610, 650, 620],
        [620, 610, 650],
    ]
    optimizer = _optimizer_with_rows(rows)

    score = optimizer._lineup_mean_score(OrderedLineup(0, (1, 2)))
    canonical_back_pair_score = optimizer._lineup_mean_score(OrderedLineup(0, (2, 1)))
    distinct_lead_score = optimizer._lineup_mean_score(OrderedLineup(1, (0, 2)))

    assert canonical_back_pair_score == score
    assert isinstance(distinct_lead_score, float)
    assert len(optimizer._lineup_mean_score_cache) == 2


def test_cached_optimizer_output_remains_deterministic_for_same_seed() -> None:
    rows = [
        [650, 620, 610, 600],
        [610, 650, 620, 600],
        [620, 610, 650, 600],
        [600, 620, 610, 650],
        [640, 640, 610, 610],
        [610, 610, 640, 640],
        [630, 610, 630, 610],
        [610, 630, 610, 630],
    ]
    optimizer_a = _optimizer_with_rows(rows)
    optimizer_b = _optimizer_with_rows(rows)

    solution_a = optimizer_a.optimize(team_size=6, restarts=1)
    solution_b = optimizer_b.optimize(team_size=6, restarts=1)

    assert solution_b == solution_a


def test_workers_one_preserves_deterministic_single_process_output() -> None:
    rows = [
        [650, 620, 610, 600],
        [610, 650, 620, 600],
        [620, 610, 650, 600],
        [600, 620, 610, 650],
        [640, 640, 610, 610],
        [610, 610, 640, 640],
        [630, 610, 630, 610],
        [610, 630, 610, 630],
    ]
    optimizer_a = _optimizer_with_rows(rows)
    optimizer_b = _optimizer_with_rows(rows)

    solution_a = optimizer_a.optimize(team_size=6, restarts=4, workers=1)
    solution_b = optimizer_b.optimize(team_size=6, restarts=4, workers=1)

    assert solution_b == solution_a


def test_workers_two_returns_deterministic_legal_result_for_fixed_inputs() -> None:
    rows = [
        [650, 620, 610, 600],
        [610, 650, 620, 600],
        [620, 610, 650, 600],
        [600, 620, 610, 650],
        [640, 640, 610, 610],
        [610, 610, 640, 640],
        [630, 610, 630, 610],
        [610, 630, 610, 630],
    ]
    optimizer_a = _optimizer_with_rows(rows)
    optimizer_b = _optimizer_with_rows(rows)

    solution_a = optimizer_a.optimize(team_size=6, restarts=4, workers=2)
    solution_b = optimizer_b.optimize(team_size=6, restarts=4, workers=2)

    assert solution_b == solution_a
    assert optimizer_a._is_team_legal(list(solution_a.member_indices))


def test_workers_greater_than_one_uses_process_executor_batches(monkeypatch) -> None:
    rows = [
        [650, 620, 610, 600],
        [610, 650, 620, 600],
        [620, 610, 650, 600],
        [600, 620, 610, 650],
        [640, 640, 610, 610],
        [610, 610, 640, 640],
        [630, 610, 630, 610],
        [610, 630, 610, 630],
    ]
    captured: dict[str, object] = {}

    class FakeProcessPoolExecutor:
        def __init__(self, max_workers: int) -> None:
            captured["max_workers"] = max_workers

        def __enter__(self) -> "FakeProcessPoolExecutor":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def map(self, func: object, batches: object) -> list[object]:
            batch_list = list(batches)
            captured["batch_restarts"] = [batch.restarts for batch in batch_list]
            captured["batch_seeds"] = [batch.seed for batch in batch_list]
            return [func(batch) for batch in batch_list]

    monkeypatch.setattr(optimizer_module, "ProcessPoolExecutor", FakeProcessPoolExecutor)
    optimizer = _optimizer_with_rows(rows)

    solution = optimizer.optimize(team_size=6, restarts=5, workers=3)

    assert captured["max_workers"] == 3
    assert captured["batch_restarts"] == [2, 2, 1]
    assert captured["batch_seeds"] == [7, 1_000_010, 2_000_013]
    assert optimizer._is_team_legal(list(solution.member_indices))


def test_optimizer_rejects_too_many_workers() -> None:
    rows = [[600, 600]] * 6
    optimizer = _optimizer_with_rows(rows)

    try:
        optimizer.optimize(team_size=6, restarts=1, workers=33)
    except ValueError as exc:
        assert str(exc) == "workers must be at most 32"
    else:
        raise AssertionError("expected workers cap validation")


def test_cached_lineup_depth_matches_canonical_lineup_scorer() -> None:
    rows = [
        [650, 620, 610, 600],
        [610, 650, 620, 600],
        [620, 610, 650, 600],
        [600, 620, 610, 650],
        [640, 640, 610, 610],
        [610, 610, 640, 640],
    ]
    optimizer = _optimizer_with_rows(rows)
    team = [0, 1, 2, 3, 4, 5]

    assert optimizer._score_team_lineups(team) == score_roster_lineup_depth(team, optimizer.matrices)
