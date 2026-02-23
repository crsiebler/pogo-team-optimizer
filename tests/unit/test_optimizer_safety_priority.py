from pogo_team_optimizer.application.optimizer import TeamOptimizer


def test_optimizer_high_safety_priority_prefers_two_safe_members() -> None:
    row_labels = ["Amon", "Bmon", "Cmon"]
    col_labels = ["Opp1", "Opp2"]
    matrices = [
        [
            [900, 900],
            [560, 560],
            [550, 550],
        ]
    ]

    optimizer = TeamOptimizer(
        row_labels,
        col_labels,
        matrices,
        bulk_by_row=[200.0, 200.0, 200.0],
        safety_by_row=[50.0, 95.0, 92.0],
        seed=7,
    )

    team = optimizer.optimize(
        team_size=2,
        restarts=40,
        safety_floor=82.0,
        min_safe_members=2,
        safe_member_floor=90.0,
    )

    assert set(team.member_indices) == {1, 2}
