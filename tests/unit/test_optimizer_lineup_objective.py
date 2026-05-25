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
