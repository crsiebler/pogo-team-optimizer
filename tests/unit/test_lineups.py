import pytest

from pogo_team_optimizer.application.lineups import (
    OrderedLineup,
    bench_utility_warnings,
    score_battle_frontier_lineup_usage,
    classify_lineup_shape,
    classify_bench_utility,
    enumerate_ordered_lineups,
    score_roster_bench_utility,
    score_ordered_lineup,
)


def _matrix_with_rows(rows: dict[int, list[int]]) -> list[list[int]]:
    matrix = [[500] for _ in range(6)]
    for row_index, values in rows.items():
        matrix[row_index] = values
    return matrix


def test_six_member_roster_produces_sixty_ordered_lineups() -> None:
    lineups = enumerate_ordered_lineups((0, 1, 2, 3, 4, 5))

    assert len(lineups) == 60
    assert len(set(lineups)) == 60


def test_each_lineup_has_one_lead_and_two_distinct_back_members() -> None:
    lineups = enumerate_ordered_lineups((0, 1, 2, 3, 4, 5))

    for lineup in lineups:
        assert len(lineup.back_indices) == 2
        assert lineup.lead_index not in lineup.back_indices
        assert lineup.back_indices[0] != lineup.back_indices[1]


def test_back_pair_order_is_canonicalized() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(2, 1))

    assert lineup.back_indices == (1, 2)


def test_back_pair_order_does_not_duplicate_lineups() -> None:
    lineups = enumerate_ordered_lineups((0, 1, 2))

    assert lineups == (
        OrderedLineup(lead_index=0, back_indices=(1, 2)),
        OrderedLineup(lead_index=1, back_indices=(0, 2)),
        OrderedLineup(lead_index=2, back_indices=(0, 1)),
    )


def test_lead_order_remains_distinct() -> None:
    lineups = enumerate_ordered_lineups((0, 1, 2, 3, 4, 5))

    assert OrderedLineup(lead_index=0, back_indices=(1, 2)) in lineups
    assert OrderedLineup(lead_index=1, back_indices=(0, 2)) in lineups


def test_lineup_enumeration_is_deterministic_for_same_input_order() -> None:
    roster = (5, 3, 9, 1, 7, 2)

    assert enumerate_ordered_lineups(roster) == enumerate_ordered_lineups(roster)


def test_lineup_enumeration_rejects_duplicate_roster_members() -> None:
    with pytest.raises(ValueError, match="roster_indices must not contain duplicates"):
        enumerate_ordered_lineups((0, 1, 1, 2))


def test_lineup_enumeration_rejects_rosters_with_fewer_than_three_members() -> None:
    with pytest.raises(ValueError, match="roster_indices must contain at least 3 members"):
        enumerate_ordered_lineups((0, 1))


def test_ordered_lineup_rejects_back_pair_containing_lead() -> None:
    with pytest.raises(ValueError, match="lead_index must be distinct from back_indices"):
        OrderedLineup(lead_index=0, back_indices=(0, 1))


def test_ordered_lineup_rejects_duplicate_back_members() -> None:
    with pytest.raises(ValueError, match="back_indices must contain two distinct members"):
        OrderedLineup(lead_index=0, back_indices=(1, 1))


def test_score_ordered_lineup_uses_balanced_one_shield_path() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    matrices = (
        _matrix_with_rows({0: [900], 1: [900], 2: [900]}),
        _matrix_with_rows({0: [410], 1: [530], 2: [620]}),
        _matrix_with_rows({0: [900], 1: [900], 2: [900]}),
    )

    score = score_ordered_lineup(lineup, matrices)

    balanced = score.path_scores[0]
    assert balanced.path_name == "balanced"
    assert balanced.best_scores == (620,)


def test_score_ordered_lineup_uses_shield_spend_path() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    matrices = (
        _matrix_with_rows({0: [100], 1: [430], 2: [610]}),
        _matrix_with_rows({0: [900], 1: [900], 2: [900]}),
        _matrix_with_rows({0: [650], 1: [100], 2: [100]}),
    )

    score = score_ordered_lineup(lineup, matrices)

    shield_spend = score.path_scores[1]
    assert shield_spend.path_name == "shield_spend"
    assert shield_spend.best_scores == (650,)


def test_score_ordered_lineup_uses_shield_save_path() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    matrices = (
        _matrix_with_rows({0: [610], 1: [100], 2: [100]}),
        _matrix_with_rows({0: [900], 1: [900], 2: [900]}),
        _matrix_with_rows({0: [100], 1: [430], 2: [650]}),
    )

    score = score_ordered_lineup(lineup, matrices)

    shield_save = score.path_scores[2]
    assert shield_save.path_name == "shield_save"
    assert shield_save.best_scores == (650,)


def test_score_ordered_lineup_uses_better_back_for_each_matchup() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    matrices = (
        _matrix_with_rows({0: [100], 1: [100], 2: [100]}),
        _matrix_with_rows({0: [390, 390], 1: [350, 650], 2: [650, 350]}),
        _matrix_with_rows({0: [100], 1: [100], 2: [100]}),
    )

    score = score_ordered_lineup(lineup, matrices)

    assert score.path_scores[0].best_scores == (650, 650)


def test_score_ordered_lineup_counts_lineup_thresholds_exclusively() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    matrices = (
        _matrix_with_rows({0: [100, 100, 100, 100, 100, 100], 1: [100] * 6, 2: [100] * 6}),
        _matrix_with_rows(
            {
                0: [399, 400, 401, 599, 600, 601],
                1: [100, 100, 100, 100, 100, 100],
                2: [100, 100, 100, 100, 100, 100],
            }
        ),
        _matrix_with_rows({0: [100, 100, 100, 100, 100, 100], 1: [100] * 6, 2: [100] * 6}),
    )

    score = score_ordered_lineup(lineup, matrices)

    balanced = score.path_scores[0]
    assert balanced.best_scores == (399, 400, 401, 599, 600, 601)
    assert balanced.overwhelming_count == 1
    assert balanced.dominate_count == 1


@pytest.mark.parametrize(
    ("lead_types", "back_one_types", "back_two_types", "expected_shape"),
    [
        (("water",), ("grass",), ("fire",), "ABC"),
        (("water",), ("fire",), ("fire", "flying"), "ABB"),
        (("water",), ("water", "flying"), ("grass",), "ABA"),
        ((), ("grass",), ("fire",), "unclassified"),
        (("water",), (), ("fire",), "unclassified"),
        (("water",), ("water",), ("water",), "unclassified"),
        (("water",), ("water", "flying"), ("flying",), "unclassified"),
    ],
)
def test_classify_lineup_shape(
    lead_types: tuple[str, ...],
    back_one_types: tuple[str, ...],
    back_two_types: tuple[str, ...],
    expected_shape: str,
) -> None:
    assert classify_lineup_shape(lead_types, back_one_types, back_two_types) == expected_shape


@pytest.mark.parametrize(
    ("lineups_used", "viable_lineup_rate", "expected_tier"),
    [
        (30, 0.50, "core"),
        (12, 0.25, "flexible"),
        (5, 0.10, "specialist"),
        (1, 0.05, "low_utility"),
        (0, 0.00, "unbringable"),
    ],
)
def test_classify_bench_utility_tiers(
    lineups_used: int,
    viable_lineup_rate: float,
    expected_tier: str,
) -> None:
    assert classify_bench_utility(lineups_used, viable_lineup_rate) == expected_tier


def test_bench_utility_warnings_cover_low_usage_and_unbringable_members() -> None:
    low_usage_warning = bench_utility_warnings("low_utility")
    unbringable_warning = bench_utility_warnings("unbringable")

    assert low_usage_warning[0].category == "bench_utility"
    assert low_usage_warning[0].code == "low_usage"
    assert low_usage_warning[0].severity == "medium"
    assert unbringable_warning[0].category == "bench_utility"
    assert unbringable_warning[0].code == "unbringable"
    assert unbringable_warning[0].severity == "high"
    assert bench_utility_warnings("core") == ()
    assert bench_utility_warnings("flexible") == ()


def test_score_roster_bench_utility_marks_members_unbringable_when_no_viable_lineups() -> None:
    weak_matrix = [[300] for _ in range(6)]

    utility = score_roster_bench_utility((0, 1, 2, 3, 4, 5), (weak_matrix, weak_matrix, weak_matrix))

    assert [usage.member_index for usage in utility] == [0, 1, 2, 3, 4, 5]
    assert {usage.tier for usage in utility} == {"unbringable"}
    assert {usage.lineups_used for usage in utility} == {0}
    assert {usage.warnings[0].code for usage in utility} == {"unbringable"}


def test_score_roster_bench_utility_counts_lead_and_back_usage_for_viable_lineups() -> None:
    matrix = [
        [650],
        [450],
        [450],
        [450],
        [450],
        [450],
    ]

    utility = score_roster_bench_utility((0, 1, 2, 3, 4, 5), (matrix, matrix, matrix))
    core = utility[0]

    assert core.tier == "core"
    assert core.lineups_used == 30
    assert core.lead_lineups_used == 10
    assert core.back_lineups_used == 20
    assert core.viable_lineup_rate == 1.0
    assert core.all_lineup_rate == 0.5
    assert core.best_lineup_score == 650.0


def test_battle_frontier_lineup_usage_counts_point_groups_across_viable_lineups() -> None:
    matrix = [
        [650],
        [640],
        [630],
        [300],
        [300],
        [300],
    ]

    diagnostics = score_battle_frontier_lineup_usage(
        (0, 1, 2, 3, 4, 5),
        (matrix, matrix, matrix),
        (0, 1, 3, 5, 0, 5),
    )

    assert diagnostics.viable_lineup_count == 57
    assert diagnostics.free_low_point_usage_rate == 87 / (57 * 3)
    assert diagnostics.high_point_usage_rate == 84 / (57 * 3)


def test_roster_bench_utility_adds_battle_frontier_warnings_for_point_usage() -> None:
    matrix = [[300] for _ in range(6)]

    utility = score_roster_bench_utility(
        (0, 1, 2, 3, 4, 5),
        (matrix, matrix, matrix),
        battle_frontier_points_by_row=(0, 1, 3, 5, 0, 5),
    )

    warnings_by_member = {
        usage.member_index: [warning.code for warning in usage.warnings]
        for usage in utility
    }

    assert "expensive_mostly_bench" in warnings_by_member[5]
    assert "low_point_paper_coverage" in warnings_by_member[4]
