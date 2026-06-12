from pogo_team_optimizer.application.optimizer import TeamOptimizer


def test_optimizer_rejects_bfmaster_teams_over_point_budget() -> None:
    optimizer = TeamOptimizer(
        row_labels=["Amon", "Bmon", "Cmon"],
        col_labels=["Opp1", "Opp2"],
        matrices=[[[900, 400], [400, 900], [600, 600]]],
        bulk_by_row=[200.0, 200.0, 200.0],
        battle_frontier_points_by_row=[6, 6, 0],
        battle_frontier_max_points=11,
        seed=7,
    )

    team = optimizer.optimize(team_size=2, restarts=20)

    assert set(team.member_indices) == {0, 2}


def test_optimizer_rejects_bfmaster_teams_with_two_five_point_members() -> None:
    optimizer = TeamOptimizer(
        row_labels=["Amon", "Bmon", "Cmon"],
        col_labels=["Opp1", "Opp2"],
        matrices=[[[900, 400], [400, 900], [600, 600]]],
        bulk_by_row=[200.0, 200.0, 200.0],
        battle_frontier_points_by_row=[5, 5, 0],
        battle_frontier_max_five_point_members=1,
        seed=7,
    )

    team = optimizer.optimize(team_size=2, restarts=20)

    assert set(team.member_indices) == {0, 2}


def test_optimizer_rejects_bfmaster_teams_with_two_mega_members() -> None:
    optimizer = TeamOptimizer(
        row_labels=["Amon (Mega)", "Bmon (Mega X)", "Cmon"],
        col_labels=["Opp1", "Opp2"],
        matrices=[[[900, 400], [400, 900], [600, 600]]],
        bulk_by_row=[200.0, 200.0, 200.0],
        battle_frontier_points_by_row=[0, 0, 0],
        battle_frontier_max_mega_members=1,
        seed=7,
    )

    team = optimizer.optimize(team_size=2, restarts=20)

    assert set(team.member_indices) == {0, 2}


def test_optimizer_random_bfmaster_seed_team_is_legal() -> None:
    optimizer = TeamOptimizer(
        row_labels=["Amon", "Bmon", "Cmon", "Dmon", "Emon"],
        col_labels=["Opp1", "Opp2"],
        matrices=[
            [
                [900, 400],
                [400, 900],
                [700, 650],
                [680, 680],
                [660, 660],
            ]
        ],
        bulk_by_row=[200.0, 200.0, 200.0, 200.0, 200.0],
        battle_frontier_points_by_row=[5, 5, 3, 3, 0],
        battle_frontier_max_points=11,
        battle_frontier_max_five_point_members=1,
        battle_frontier_max_mega_members=1,
        seed=7,
    )

    team = optimizer._random_team(team_size=4)

    assert sum(optimizer.battle_frontier_points_by_row[idx] for idx in team) <= 11
    assert sum(optimizer.battle_frontier_points_by_row[idx] == 5 for idx in team) <= 1


def test_optimizer_workers_two_preserves_bfmaster_legality() -> None:
    optimizer_a = TeamOptimizer(
        row_labels=["Amon", "Bmon", "Cmon", "Dmon", "Emon"],
        col_labels=["Opp1", "Opp2"],
        matrices=[
            [
                [900, 400],
                [400, 900],
                [700, 650],
                [680, 680],
                [660, 660],
            ]
        ],
        bulk_by_row=[200.0, 200.0, 200.0, 200.0, 200.0],
        battle_frontier_points_by_row=[5, 5, 3, 3, 0],
        battle_frontier_max_points=11,
        battle_frontier_max_five_point_members=1,
        battle_frontier_max_mega_members=1,
        seed=7,
    )
    optimizer_b = TeamOptimizer(
        row_labels=["Amon", "Bmon", "Cmon", "Dmon", "Emon"],
        col_labels=["Opp1", "Opp2"],
        matrices=[
            [
                [900, 400],
                [400, 900],
                [700, 650],
                [680, 680],
                [660, 660],
            ]
        ],
        bulk_by_row=[200.0, 200.0, 200.0, 200.0, 200.0],
        battle_frontier_points_by_row=[5, 5, 3, 3, 0],
        battle_frontier_max_points=11,
        battle_frontier_max_five_point_members=1,
        battle_frontier_max_mega_members=1,
        seed=7,
    )

    team = optimizer_a.optimize(team_size=4, restarts=4, workers=2)
    same_seed_team = optimizer_b.optimize(team_size=4, restarts=4, workers=2)

    assert same_seed_team == team
    assert sum(optimizer_a.battle_frontier_points_by_row[idx] for idx in team.member_indices) <= 11
    assert sum(optimizer_a.battle_frontier_points_by_row[idx] == 5 for idx in team.member_indices) <= 1
