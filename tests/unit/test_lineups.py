import pytest

from pogo_team_optimizer.application.lineups import (
    OrderedLineup,
    bench_utility_warnings,
    calculate_lineup_role_fit,
    calculate_lineup_synergy,
    classify_bench_utility,
    classify_lineup_shape,
    enumerate_ordered_lineups,
    score_battle_frontier_lineup_usage,
    score_ordered_lineup,
    score_roster_bench_utility,
)
from pogo_team_optimizer.domain.models import RankingCategory, RankingProfile, RankingRow


def _matrix_with_rows(rows: dict[int, list[int]]) -> list[list[int]]:
    matrix = [[500] for _ in range(6)]
    for row_index, values in rows.items():
        matrix[row_index] = values
    return matrix


def _synergy_type_chart() -> dict[str, dict[str, float]]:
    return {
        "electric": {"water": 1.6, "flying": 1.6, "grass": 0.625, "ground": 0.39},
        "grass": {"water": 1.6, "ground": 1.6, "fire": 0.625, "flying": 0.625},
        "water": {"fire": 1.6, "ground": 1.6, "grass": 0.625, "water": 0.625},
        "fire": {"grass": 1.6, "steel": 1.6, "water": 0.625, "fire": 0.625},
        "rock": {"fire": 1.6, "flying": 1.6, "water": 0.625, "ground": 0.625},
        "ground": {"electric": 1.6, "fire": 1.6, "grass": 0.625, "flying": 0.39},
        "ice": {"grass": 1.6, "flying": 1.6, "water": 0.625, "fire": 0.625},
    }


def _complete_water_grass_flying_chart() -> dict[str, dict[str, float]]:
    return {
        "electric": {"water": 1.6, "flying": 1.6, "grass": 0.625},
        "grass": {"water": 1.6, "flying": 0.625, "grass": 0.625},
        "water": {"water": 0.625, "flying": 1.0, "grass": 0.625},
        "flying": {"water": 1.0, "flying": 1.0, "grass": 1.6},
    }


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


def test_calculate_lineup_role_fit_uses_lead_and_back_role_categories() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    profile = RankingProfile(
        scores_by_category={
            RankingCategory.LEADS: {
                "Amon": RankingRow("Amon", 90.0, normalized_score=0.9),
            },
            RankingCategory.SWITCHES: {
                "Bmon": RankingRow("Bmon", 80.0, normalized_score=0.8),
                "Cmon": RankingRow("Cmon", 20.0, normalized_score=0.2),
            },
            RankingCategory.CLOSERS: {
                "Bmon": RankingRow("Bmon", 60.0, normalized_score=0.6),
                "Cmon": RankingRow("Cmon", 40.0, normalized_score=0.4),
            },
            RankingCategory.ATTACKERS: {
                "Bmon": RankingRow("Bmon", 70.0, normalized_score=0.7),
                "Cmon": RankingRow("Cmon", 30.0, normalized_score=0.3),
            },
            RankingCategory.CHARGERS: {
                "Bmon": RankingRow("Bmon", 50.0, normalized_score=0.5),
                "Cmon": RankingRow("Cmon", 50.0, normalized_score=0.5),
            },
            RankingCategory.CONSISTENCY: {
                "Bmon": RankingRow("Bmon", 90.0, normalized_score=0.9),
                "Cmon": RankingRow("Cmon", 10.0, normalized_score=0.1),
            },
        }
    )

    role_fit = calculate_lineup_role_fit(
        lineup,
        ("Amon", "Bmon", "Cmon"),
        profile,
    )

    assert role_fit.score == 0.65
    assert role_fit.components == {
        "lead_leads": 0.9,
        "back_switches": 0.5,
        "back_closers": 0.5,
        "back_attackers": 0.5,
        "back_chargers": 0.5,
        "back_consistency": 0.5,
    }


def test_calculate_lineup_role_fit_weights_distinct_components() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    profile = RankingProfile(
        scores_by_category={
            RankingCategory.LEADS: {"Amon": RankingRow("Amon", 80.0, normalized_score=0.8)},
            RankingCategory.SWITCHES: {
                "Bmon": RankingRow("Bmon", 30.0, normalized_score=0.3),
                "Cmon": RankingRow("Cmon", 50.0, normalized_score=0.5),
            },
            RankingCategory.CLOSERS: {
                "Bmon": RankingRow("Bmon", 40.0, normalized_score=0.4),
                "Cmon": RankingRow("Cmon", 60.0, normalized_score=0.6),
            },
            RankingCategory.ATTACKERS: {
                "Bmon": RankingRow("Bmon", 50.0, normalized_score=0.5),
                "Cmon": RankingRow("Cmon", 70.0, normalized_score=0.7),
            },
            RankingCategory.CHARGERS: {
                "Bmon": RankingRow("Bmon", 60.0, normalized_score=0.6),
                "Cmon": RankingRow("Cmon", 80.0, normalized_score=0.8),
            },
            RankingCategory.CONSISTENCY: {
                "Bmon": RankingRow("Bmon", 20.0, normalized_score=0.2),
                "Cmon": RankingRow("Cmon", 40.0, normalized_score=0.4),
            },
        }
    )

    role_fit = calculate_lineup_role_fit(lineup, ("Amon", "Bmon", "Cmon"), profile)

    assert role_fit.components.keys() == {
        "lead_leads",
        "back_switches",
        "back_closers",
        "back_attackers",
        "back_chargers",
        "back_consistency",
    }
    assert role_fit.components == pytest.approx(
        {
            "lead_leads": 0.8,
            "back_switches": 0.4,
            "back_closers": 0.5,
            "back_attackers": 0.6,
            "back_chargers": 0.7,
            "back_consistency": 0.3,
        }
    )
    assert role_fit.score == pytest.approx(0.59)


def test_score_ordered_lineup_blends_role_fit_without_changing_resource_paths() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    matrices = (
        _matrix_with_rows({0: [500], 1: [500], 2: [500]}),
        _matrix_with_rows({0: [500], 1: [500], 2: [500]}),
        _matrix_with_rows({0: [500], 1: [500], 2: [500]}),
    )
    profile = RankingProfile(
        scores_by_category={
            RankingCategory.LEADS: {"Amon": RankingRow("Amon", 100.0, normalized_score=1.0)},
            RankingCategory.SWITCHES: {
                "Bmon": RankingRow("Bmon", 100.0, normalized_score=1.0),
                "Cmon": RankingRow("Cmon", 100.0, normalized_score=1.0),
            },
            RankingCategory.CLOSERS: {
                "Bmon": RankingRow("Bmon", 100.0, normalized_score=1.0),
                "Cmon": RankingRow("Cmon", 100.0, normalized_score=1.0),
            },
            RankingCategory.ATTACKERS: {
                "Bmon": RankingRow("Bmon", 100.0, normalized_score=1.0),
                "Cmon": RankingRow("Cmon", 100.0, normalized_score=1.0),
            },
            RankingCategory.CHARGERS: {
                "Bmon": RankingRow("Bmon", 100.0, normalized_score=1.0),
                "Cmon": RankingRow("Cmon", 100.0, normalized_score=1.0),
            },
            RankingCategory.CONSISTENCY: {
                "Bmon": RankingRow("Bmon", 100.0, normalized_score=1.0),
                "Cmon": RankingRow("Cmon", 100.0, normalized_score=1.0),
            },
        }
    )

    score = score_ordered_lineup(
        lineup,
        matrices,
        species_by_row=("Amon", "Bmon", "Cmon"),
        ranking_profile=profile,
    )

    assert [path.mean_best_score for path in score.path_scores] == [500.0, 500.0, 500.0]
    assert score.resource_mean_score == 500.0
    assert score.role_fit_score == 1.0
    assert score.lineup_score == 515.0


def test_abc_synergy_rewards_complementary_strengths_and_low_shared_weakness() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    matrices = (
        _matrix_with_rows({0: [650, 450, 450], 1: [450, 650, 450], 2: [450, 450, 650]}),
        _matrix_with_rows({0: [650, 450, 450], 1: [450, 650, 450], 2: [450, 450, 650]}),
        _matrix_with_rows({0: [650, 450, 450], 1: [450, 650, 450], 2: [450, 450, 650]}),
    )

    synergy = calculate_lineup_synergy(
        lineup,
        matrices,
        pokemon_types_by_row=(("water",), ("fire",), ("grass",)),
        type_effectiveness=_synergy_type_chart(),
    )

    assert synergy.components["shape"] == "ABC"
    assert synergy.components["shared_weakness_pressure"] == 0.0
    assert synergy.components["winner_diversity"] == 1.0
    assert synergy.score > 0.75


def test_abb_synergy_rewards_singleton_covering_back_pair_shared_weakness() -> None:
    covered = calculate_lineup_synergy(
        OrderedLineup(lead_index=0, back_indices=(1, 2)),
        (
            _matrix_with_rows({0: [650], 1: [450], 2: [450]}),
            _matrix_with_rows({0: [650], 1: [450], 2: [450]}),
            _matrix_with_rows({0: [650], 1: [450], 2: [450]}),
        ),
        pokemon_types_by_row=(("grass",), ("water",), ("water", "flying")),
        type_effectiveness=_synergy_type_chart(),
    )
    uncovered = calculate_lineup_synergy(
        OrderedLineup(lead_index=0, back_indices=(1, 2)),
        (
            _matrix_with_rows({0: [450], 1: [450], 2: [450]}),
            _matrix_with_rows({0: [450], 1: [450], 2: [450]}),
            _matrix_with_rows({0: [450], 1: [450], 2: [450]}),
        ),
        pokemon_types_by_row=(("fire",), ("water",), ("water", "flying")),
        type_effectiveness=_synergy_type_chart(),
    )

    assert covered.components["shape"] == "ABB"
    assert covered.components["singleton_covers_pair_weakness"] > 0.0
    assert covered.score > uncovered.score


def test_abb_synergy_rewards_combined_back_pair_coverage() -> None:
    synergy = calculate_lineup_synergy(
        OrderedLineup(lead_index=0, back_indices=(1, 2)),
        (
            _matrix_with_rows({0: [450], 1: [450], 2: [450]}),
            _matrix_with_rows({0: [450], 1: [450], 2: [450]}),
            _matrix_with_rows({0: [450], 1: [450], 2: [450]}),
        ),
        pokemon_types_by_row=(
            ("lead",),
            ("shared_back", "x_resist"),
            ("shared_back", "y_resist"),
        ),
        type_effectiveness={
            "x": {"lead": 1.6, "shared_back": 1.0, "x_resist": 0.625, "y_resist": 1.0},
            "y": {"lead": 1.6, "shared_back": 1.0, "x_resist": 1.0, "y_resist": 0.625},
        },
    )

    assert synergy.components["shape"] == "ABB"
    assert synergy.components["pair_covers_singleton_weakness"] == 1.0


def test_aba_synergy_penalizes_lead_shared_weakness_with_only_b_answer() -> None:
    unsafe = calculate_lineup_synergy(
        OrderedLineup(lead_index=0, back_indices=(1, 2)),
        (
            _matrix_with_rows({0: [350], 1: [650], 2: [350]}),
            _matrix_with_rows({0: [350], 1: [650], 2: [350]}),
            _matrix_with_rows({0: [350], 1: [650], 2: [350]}),
        ),
        pokemon_types_by_row=(("water",), ("grass",), ("water", "flying")),
        type_effectiveness=_synergy_type_chart(),
    )
    safer = calculate_lineup_synergy(
        OrderedLineup(lead_index=0, back_indices=(1, 2)),
        (
            _matrix_with_rows({0: [350], 1: [650], 2: [650]}),
            _matrix_with_rows({0: [350], 1: [650], 2: [650]}),
            _matrix_with_rows({0: [350], 1: [650], 2: [650]}),
        ),
        pokemon_types_by_row=(("water",), ("grass",), ("water", "flying")),
        type_effectiveness=_synergy_type_chart(),
    )

    assert unsafe.components["shape"] == "ABA"
    assert unsafe.components["unsafe_aba_shared_weakness"] > 0.0
    assert unsafe.score < safer.score


def test_aba_synergy_penalizes_uncovered_shared_weakness() -> None:
    synergy = calculate_lineup_synergy(
        OrderedLineup(lead_index=0, back_indices=(1, 2)),
        (
            _matrix_with_rows({0: [450], 1: [450], 2: [450]}),
            _matrix_with_rows({0: [450], 1: [450], 2: [450]}),
            _matrix_with_rows({0: [450], 1: [450], 2: [450]}),
        ),
        pokemon_types_by_row=(("water",), ("fire",), ("water", "flying")),
        type_effectiveness=_synergy_type_chart(),
    )

    assert synergy.components["shape"] == "ABA"
    assert synergy.components["unsafe_aba_shared_weakness"] > 0.0
    assert synergy.score < 0.5


def test_aba_synergy_rewards_redundant_answers_to_weighted_top_threats() -> None:
    beneficial = calculate_lineup_synergy(
        OrderedLineup(lead_index=0, back_indices=(1, 2)),
        (
            _matrix_with_rows({0: [650, 450], 1: [450, 450], 2: [650, 450]}),
            _matrix_with_rows({0: [650, 450], 1: [450, 450], 2: [650, 450]}),
            _matrix_with_rows({0: [650, 450], 1: [450, 450], 2: [650, 450]}),
        ),
        pokemon_types_by_row=(("water",), ("grass",), ("water", "flying")),
        type_effectiveness=_synergy_type_chart(),
        threat_weights=(0.9, 0.1),
    )
    neutral = calculate_lineup_synergy(
        OrderedLineup(lead_index=0, back_indices=(1, 2)),
        (
            _matrix_with_rows({0: [450, 450], 1: [450, 450], 2: [450, 450]}),
            _matrix_with_rows({0: [450, 450], 1: [450, 450], 2: [450, 450]}),
            _matrix_with_rows({0: [450, 450], 1: [450, 450], 2: [450, 450]}),
        ),
        pokemon_types_by_row=(("water",), ("grass",), ("water", "flying")),
        type_effectiveness=_synergy_type_chart(),
        threat_weights=(0.9, 0.1),
    )

    assert beneficial.components["shape"] == "ABA"
    assert beneficial.components["aba_redundant_strength"] == 0.9
    assert beneficial.score > neutral.score


def test_score_ordered_lineup_skips_synergy_when_lineup_member_types_are_missing() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    matrices = (
        _matrix_with_rows({0: [600], 1: [600], 2: [600]}),
        _matrix_with_rows({0: [600], 1: [600], 2: [600]}),
        _matrix_with_rows({0: [600], 1: [600], 2: [600]}),
    )

    score = score_ordered_lineup(
        lineup,
        matrices,
        pokemon_types_by_row=((), ("grass",), ("water",)),
        type_effectiveness=_synergy_type_chart(),
    )

    assert score.resource_mean_score == 600.0
    assert score.synergy_score is None
    assert score.lineup_score == 600.0


def test_score_ordered_lineup_skips_synergy_when_type_chart_is_incomplete() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    matrices = (
        _matrix_with_rows({0: [600], 1: [600], 2: [600]}),
        _matrix_with_rows({0: [600], 1: [600], 2: [600]}),
        _matrix_with_rows({0: [600], 1: [600], 2: [600]}),
    )

    score = score_ordered_lineup(
        lineup,
        matrices,
        pokemon_types_by_row=(("water",), ("fire",), ("grass",)),
        type_effectiveness={"electric": {"water": 1.6}},
    )

    assert score.resource_mean_score == 600.0
    assert score.synergy_score is None
    assert score.lineup_score == 600.0


def test_score_ordered_lineup_skips_synergy_when_type_chart_attack_rows_are_incomplete() -> None:
    lineup = OrderedLineup(lead_index=0, back_indices=(1, 2))
    matrices = (
        _matrix_with_rows({0: [600], 1: [600], 2: [600]}),
        _matrix_with_rows({0: [600], 1: [600], 2: [600]}),
        _matrix_with_rows({0: [600], 1: [600], 2: [600]}),
    )

    score = score_ordered_lineup(
        lineup,
        matrices,
        pokemon_types_by_row=(("water",), ("fire",), ("grass",)),
        type_effectiveness={"electric": {"water": 1.6, "fire": 1.0, "grass": 0.625}},
    )

    assert score.resource_mean_score == 600.0
    assert score.synergy_score is None
    assert score.lineup_score == 600.0


def test_lineup_role_fit_keeps_back_pair_unordered() -> None:
    profile = RankingProfile(
        scores_by_category={
            RankingCategory.LEADS: {"Amon": RankingRow("Amon", 50.0, normalized_score=0.5)},
            RankingCategory.SWITCHES: {
                "Bmon": RankingRow("Bmon", 100.0, normalized_score=1.0),
                "Cmon": RankingRow("Cmon", 0.0, normalized_score=0.0),
            },
            RankingCategory.CLOSERS: {
                "Bmon": RankingRow("Bmon", 0.0, normalized_score=0.0),
                "Cmon": RankingRow("Cmon", 100.0, normalized_score=1.0),
            },
        }
    )

    role_fit = calculate_lineup_role_fit(
        OrderedLineup(lead_index=0, back_indices=(2, 1)),
        ("Amon", "Bmon", "Cmon"),
        profile,
    )

    assert role_fit.components["back_switches"] == 0.5
    assert role_fit.components["back_closers"] == 0.5
    assert role_fit.score == 0.5


def test_lineup_role_fit_uses_neutral_fallback_for_missing_normalized_scores() -> None:
    profile = RankingProfile(
        scores_by_category={
            RankingCategory.LEADS: {"Amon": RankingRow("Amon", 50.0, normalized_score=None)},
            RankingCategory.SWITCHES: {"Bmon": RankingRow("Bmon", 50.0, normalized_score=None)},
        }
    )

    role_fit = calculate_lineup_role_fit(
        OrderedLineup(lead_index=0, back_indices=(1, 2)),
        ("Amon", "Bmon", "Cmon"),
        profile,
    )

    assert set(role_fit.components.values()) == {0.5}
    assert role_fit.score == 0.5


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

    utility = score_roster_bench_utility(
        (0, 1, 2, 3, 4, 5), (weak_matrix, weak_matrix, weak_matrix)
    )

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


def test_battle_frontier_lineup_usage_uses_blended_synergy_viability() -> None:
    matrices = (
        _matrix_with_rows({0: [350], 1: [501], 2: [350]}),
        _matrix_with_rows({0: [350], 1: [501], 2: [350]}),
        _matrix_with_rows({0: [350], 1: [501], 2: [350]}),
    )

    diagnostics = score_battle_frontier_lineup_usage(
        (0, 1, 2),
        matrices,
        (0, 1, 3),
        pokemon_types_by_row=(("water",), ("grass",), ("water", "flying")),
        type_effectiveness=_complete_water_grass_flying_chart(),
        threat_weights=(1.0,),
    )

    assert diagnostics.viable_lineup_count == 1


def test_roster_bench_utility_adds_battle_frontier_warnings_for_point_usage() -> None:
    matrix = [[300] for _ in range(6)]

    utility = score_roster_bench_utility(
        (0, 1, 2, 3, 4, 5),
        (matrix, matrix, matrix),
        battle_frontier_points_by_row=(0, 1, 3, 5, 0, 5),
    )

    warnings_by_member = {
        usage.member_index: [warning.code for warning in usage.warnings] for usage in utility
    }

    assert "expensive_mostly_bench" in warnings_by_member[5]
    assert "low_point_paper_coverage" in warnings_by_member[4]
