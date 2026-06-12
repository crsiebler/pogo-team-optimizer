from dataclasses import FrozenInstanceError

import pytest

from pogo_team_optimizer.application.scoring import (
    DEFAULT_ROSTER_SCORE_WEIGHTS,
    NORMALIZED_PVPOKE_SCORE_FALLBACK,
    ROSTER_COMPONENT_ORDER,
    BulkScore,
    ConsistencyScore,
    DefensiveRatioScore,
    OffensiveRatioScore,
    PvPokeScoreNormalizationPolicy,
    RoleFitScore,
    RosterScore,
    RosterScoreWeights,
    SafetyScore,
    SynergyScore,
    ThreatCoverageScore,
    aggregate_shield_matchup_score,
    calculate_ranking_aware_roster_score,
    classify_soft_matchup_score,
    count_playable_soft_answers,
    shield_stability_score,
    soft_matchup_quality,
    soft_matchup_risk,
)
from pogo_team_optimizer.domain.models import RankingCategory, RankingProfile, RankingRow


def test_roster_score_calculates_weighted_sum() -> None:
    score = RosterScore.from_components(
        synergy=SynergyScore(0.8),
        threat_coverage=ThreatCoverageScore(0.7),
        safety=SafetyScore(0.6),
        consistency=ConsistencyScore(0.5),
        bulk=BulkScore(0.4),
        defensive_ratio=DefensiveRatioScore(0.3),
        offensive_ratio=OffensiveRatioScore(0.2),
        role_fit=RoleFitScore(0.1),
    )

    assert score.final_score == pytest.approx(
        (0.8 * DEFAULT_ROSTER_SCORE_WEIGHTS.synergy)
        + (0.7 * DEFAULT_ROSTER_SCORE_WEIGHTS.threat_coverage)
        + (0.6 * DEFAULT_ROSTER_SCORE_WEIGHTS.safety)
        + (0.5 * DEFAULT_ROSTER_SCORE_WEIGHTS.consistency)
        + (0.4 * DEFAULT_ROSTER_SCORE_WEIGHTS.bulk)
        + (0.3 * DEFAULT_ROSTER_SCORE_WEIGHTS.defensive_ratio)
        + (0.2 * DEFAULT_ROSTER_SCORE_WEIGHTS.offensive_ratio)
        + (0.1 * DEFAULT_ROSTER_SCORE_WEIGHTS.role_fit)
    )


def test_roster_score_keeps_missing_components_neutral_and_diagnostic() -> None:
    score = RosterScore.from_components(synergy=SynergyScore(0.8))

    components = {component.name: component for component in score.components}
    assert components["synergy"].weighted_score == pytest.approx(
        0.8 * DEFAULT_ROSTER_SCORE_WEIGHTS.synergy
    )
    assert components["role_fit"].raw_value is None
    assert components["role_fit"].weighted_score == 0.0
    assert components["role_fit"].diagnostics == (("missing", True),)


def test_roster_score_emits_components_in_deterministic_order() -> None:
    score = RosterScore.from_components(
        role_fit=RoleFitScore(1.0),
        synergy=SynergyScore(1.0),
        offensive_ratio=OffensiveRatioScore(1.0),
    )

    assert tuple(component.name for component in score.components) == ROSTER_COMPONENT_ORDER
    assert tuple(diagnostic["name"] for diagnostic in score.diagnostics) == ROSTER_COMPONENT_ORDER


def test_component_diagnostics_are_deterministically_ordered() -> None:
    score = RosterScore.from_components(
        safety=SafetyScore(
            0.5,
            diagnostics=(
                ("single_answer_threats", 2),
                ("no_answer_threats", 1),
            ),
        )
    )

    safety = next(component for component in score.components if component.name == "safety")
    assert safety.diagnostics == (("no_answer_threats", 1), ("single_answer_threats", 2))


def test_component_diagnostics_allow_object_values_with_duplicate_keys() -> None:
    score = RosterScore.from_components(
        safety=SafetyScore(
            0.5,
            diagnostics=(
                ("risk", {"threat": "Clodsire"}),
                ("risk", ["Lickilicky"]),
                ("count", 2),
            ),
        )
    )

    safety = next(component for component in score.components if component.name == "safety")
    expected_diagnostics = (
        ("count", 2),
        ("risk", {"threat": "Clodsire"}),
        ("risk", ["Lickilicky"]),
    )
    assert safety.diagnostics == expected_diagnostics
    safety_diagnostics = next(
        diagnostic for diagnostic in score.diagnostics if diagnostic["name"] == "safety"
    )
    assert safety_diagnostics["diagnostics"] == expected_diagnostics


def test_roster_score_honors_custom_weights() -> None:
    score = RosterScore.from_components(
        synergy=SynergyScore(0.8),
        role_fit=RoleFitScore(0.4),
        weights=RosterScoreWeights(
            synergy=1.0,
            threat_coverage=0.0,
            safety=0.0,
            consistency=0.0,
            bulk=0.0,
            defensive_ratio=0.0,
            offensive_ratio=0.0,
            role_fit=0.5,
        ),
    )

    assert score.final_score == pytest.approx(1.0)


def test_score_structures_are_immutable() -> None:
    score = RosterScore.from_components(synergy=SynergyScore(0.8))

    with pytest.raises(FrozenInstanceError):
        score.breakdown = score.breakdown


def test_default_roster_weights_cover_all_components() -> None:
    assert DEFAULT_ROSTER_SCORE_WEIGHTS.as_mapping() == {
        "synergy": 0.24,
        "threat_coverage": 0.21,
        "safety": 0.17,
        "consistency": 0.13,
        "bulk": 0.10,
        "defensive_ratio": 0.07,
        "offensive_ratio": 0.05,
        "role_fit": 0.03,
    }


def test_pvpoke_normalization_scales_category_scores_between_zero_and_one() -> None:
    profile = RankingProfile(
        scores_by_category={
            RankingCategory.LEADS: {
                "Top": RankingRow("Top", 100.0),
                "Middle": RankingRow("Middle", 50.0),
                "Low": RankingRow("Low", 0.0),
            }
        }
    )

    normalized = PvPokeScoreNormalizationPolicy().normalize_profile(profile)

    rows = normalized.scores_by_category[RankingCategory.LEADS]
    assert rows["Top"].score == 100.0
    assert rows["Top"].normalized_score == 1.0
    assert rows["Middle"].normalized_score == 0.5
    assert rows["Low"].normalized_score == 0.0


def test_pvpoke_normalization_uses_neutral_fallback_for_equal_scores() -> None:
    profile = RankingProfile(
        scores_by_category={
            RankingCategory.CONSISTENCY: {
                "Stable": RankingRow("Stable", 80.0),
                "Also Stable": RankingRow("Also Stable", 80.0),
            }
        }
    )

    normalized = PvPokeScoreNormalizationPolicy().normalize_profile(profile)

    assert tuple(
        row.normalized_score
        for row in normalized.scores_by_category[RankingCategory.CONSISTENCY].values()
    ) == (NORMALIZED_PVPOKE_SCORE_FALLBACK, NORMALIZED_PVPOKE_SCORE_FALLBACK)


def test_pvpoke_normalization_getter_defaults_missing_species_and_categories() -> None:
    profile = RankingProfile(scores_by_category={RankingCategory.SWITCHES: {}})
    policy = PvPokeScoreNormalizationPolicy()

    assert policy.get_normalized_score(profile, RankingCategory.SWITCHES, "Missing") == 0.5
    assert policy.get_normalized_score(profile, RankingCategory.CLOSERS, "Missing") == 0.5


def test_pvpoke_normalization_treats_invalid_scores_as_missing() -> None:
    profile = RankingProfile(
        scores_by_category={
            RankingCategory.ATTACKERS: {
                "Valid High": RankingRow("Valid High", 95.0),
                "Valid Low": RankingRow("Valid Low", 85.0),
                "NaN": RankingRow("NaN", float("nan")),
                "Infinite": RankingRow("Infinite", float("inf")),
                "Negative": RankingRow("Negative", -1.0),
                "Too High": RankingRow("Too High", 101.0),
            }
        }
    )

    normalized = PvPokeScoreNormalizationPolicy().normalize_profile(profile)
    rows = normalized.scores_by_category[RankingCategory.ATTACKERS]

    assert rows["Valid High"].normalized_score == 1.0
    assert rows["Valid Low"].normalized_score == 0.0
    assert rows["NaN"].normalized_score is None
    assert rows["Infinite"].normalized_score is None
    assert rows["Negative"].normalized_score is None
    assert rows["Too High"].normalized_score is None

    policy = PvPokeScoreNormalizationPolicy()
    assert policy.get_normalized_score(profile, RankingCategory.ATTACKERS, "NaN") == 0.5
    assert policy.get_normalized_score(profile, RankingCategory.ATTACKERS, "Infinite") == 0.5
    assert policy.get_normalized_score(profile, RankingCategory.ATTACKERS, "Negative") == 0.5
    assert policy.get_normalized_score(profile, RankingCategory.ATTACKERS, "Too High") == 0.5


def test_pvpoke_normalization_output_order_is_deterministic() -> None:
    profile = RankingProfile(
        scores_by_category={
            RankingCategory.CHARGERS: {
                "Zed": RankingRow("Zed", 70.0),
                "Alpha": RankingRow("Alpha", 90.0),
                "Middle": RankingRow("Middle", 80.0),
            }
        }
    )

    normalized = PvPokeScoreNormalizationPolicy().normalize_profile(profile)

    assert tuple(normalized.scores_by_category[RankingCategory.CHARGERS]) == (
        "Alpha",
        "Middle",
        "Zed",
    )


@pytest.mark.parametrize("fallback_score", [float("nan"), float("inf"), -0.1, 1.1])
def test_pvpoke_normalization_rejects_invalid_fallback_scores(fallback_score: float) -> None:
    with pytest.raises(ValueError, match="fallback_score"):
        PvPokeScoreNormalizationPolicy(fallback_score=fallback_score)


def test_shield_aggregation_uses_weighted_available_scenarios() -> None:
    assert aggregate_shield_matchup_score((300, 700, 500)) == pytest.approx(
        (300 * 0.30) + (700 * 0.50) + (500 * 0.20)
    )
    assert aggregate_shield_matchup_score((300, 700)) == pytest.approx(
        ((300 * 0.30) + (700 * 0.50)) / (0.30 + 0.50)
    )


@pytest.mark.parametrize("scores", [(), (500, 500, 500, 500), (500, float("nan"), 500)])
def test_shield_aggregation_rejects_invalid_inputs(scores: tuple[float, ...]) -> None:
    with pytest.raises(ValueError, match="shield matchup scores"):
        aggregate_shield_matchup_score(scores)


def test_soft_matchup_scoring_distinguishes_quality_bands() -> None:
    hard_loss = soft_matchup_quality(300)
    soft_loss = soft_matchup_quality(450)
    neutral = soft_matchup_quality(500)
    playable = soft_matchup_quality(560)
    strong = soft_matchup_quality(650)

    assert hard_loss < soft_loss < neutral < playable < strong
    assert classify_soft_matchup_score(650) == "strong_answer"
    assert classify_soft_matchup_score(560) == "playable_answer"
    assert classify_soft_matchup_score(500) == "neutral_matchup"
    assert classify_soft_matchup_score(450) == "soft_loss"
    assert classify_soft_matchup_score(300) == "hard_loss"


@pytest.mark.parametrize("score", [float("nan"), float("inf")])
def test_soft_matchup_classification_rejects_non_finite_scores(score: float) -> None:
    with pytest.raises(ValueError, match="matchup score"):
        classify_soft_matchup_score(score)


def test_soft_matchup_risk_penalizes_hard_losses_more_than_marginal_losses() -> None:
    assert soft_matchup_risk(300) > soft_matchup_risk(475)
    assert soft_matchup_risk(475) > soft_matchup_risk(525)


def test_playable_answer_count_rewards_multiple_stable_answers() -> None:
    stable_team = ((540, 550, 545), (530, 535, 525))
    volatile_team = ((700, 300, 300),)

    assert count_playable_soft_answers(stable_team) > count_playable_soft_answers(volatile_team)


def test_shield_stability_penalizes_isolated_shield_spikes() -> None:
    assert shield_stability_score((540, 550, 545)) > shield_stability_score((700, 300, 300))


def test_ranking_aware_roster_score_weights_top_threat_misses_above_full_meta_misses() -> None:
    matrices = [
        [
            [300, 700, 700, 700],
            [300, 700, 700, 700],
            [300, 700, 700, 700],
        ],
        [
            [300, 700, 700, 700],
            [300, 700, 700, 700],
            [300, 700, 700, 700],
        ],
        [
            [300, 700, 700, 700],
            [300, 700, 700, 700],
            [300, 700, 700, 700],
        ],
    ]

    top_miss = calculate_ranking_aware_roster_score(
        team_indices=[0, 1, 2],
        matrices=matrices,
        bulk_by_row=[100.0, 100.0, 100.0],
        top_threat_indices=(0,),
        full_meta_indices=(0, 1, 2, 3),
    )
    full_meta_only_miss = calculate_ranking_aware_roster_score(
        team_indices=[0, 1, 2],
        matrices=matrices,
        bulk_by_row=[100.0, 100.0, 100.0],
        top_threat_indices=(1,),
        full_meta_indices=(0, 1, 2, 3),
    )

    top_coverage = next(
        component for component in top_miss.components if component.name == "threat_coverage"
    )
    full_meta_coverage = next(
        component for component in full_meta_only_miss.components if component.name == "threat_coverage"
    )
    assert top_coverage.raw_value < full_meta_coverage.raw_value
    assert ("top_threat_no_answer", 1) in top_coverage.diagnostics
    assert ("full_meta_no_answer", 1) in full_meta_coverage.diagnostics


def test_ranking_aware_roster_score_honors_empty_explicit_threat_pools() -> None:
    default_score = calculate_ranking_aware_roster_score(
        team_indices=[0, 1, 2],
        matrices=[[[300], [300], [300]]] * 3,
        bulk_by_row=[100.0, 100.0, 100.0],
    )
    empty_pool_score = calculate_ranking_aware_roster_score(
        team_indices=[0, 1, 2],
        matrices=[[[300], [300], [300]]] * 3,
        bulk_by_row=[100.0, 100.0, 100.0],
        top_threat_indices=(),
        full_meta_indices=(),
    )

    default_coverage = next(
        component for component in default_score.components if component.name == "threat_coverage"
    )
    empty_pool_coverage = next(
        component for component in empty_pool_score.components if component.name == "threat_coverage"
    )
    assert default_coverage.raw_value < empty_pool_coverage.raw_value
    assert ("top_threat_no_answer", 0) in empty_pool_coverage.diagnostics
    assert ("full_meta_no_answer", 0) in empty_pool_coverage.diagnostics


def test_ranking_aware_roster_score_covers_safety_consistency_bulk_and_type_ratios() -> None:
    matrices = [
        [[620, 300], [520, 450], [480, 620]],
        [[620, 300], [520, 450], [480, 620]],
        [[620, 300], [520, 450], [480, 620]],
    ]
    type_effectiveness = {
        "electric": {"water": 1.6, "flying": 1.6, "grass": 0.625},
        "grass": {"water": 1.6, "flying": 0.625, "grass": 0.625},
        "water": {"water": 0.625, "flying": 1.0, "grass": 0.625},
    }

    score = calculate_ranking_aware_roster_score(
        team_indices=[0, 1, 2],
        matrices=matrices,
        bulk_by_row=[100.0, 150.0, 200.0],
        safety_by_row=[0.8, 0.6, 0.4],
        consistency_by_row=[0.9, 0.7, 0.5],
        pokemon_types_by_row=[("water",), ("flying",), ("grass",)],
        move_types_by_row=[("grass",), ("water",), ("electric",)],
        opponent_types_by_col=[("water",), ("flying",)],
        type_effectiveness=type_effectiveness,
        top_threat_indices=(0,),
        full_meta_indices=(0, 1),
    )

    components = {component.name: component for component in score.components}
    assert components["safety"].raw_value == pytest.approx(0.8975)
    assert components["consistency"].raw_value == pytest.approx(0.77)
    assert components["bulk"].raw_value == pytest.approx(0.5)
    assert components["defensive_ratio"].raw_value is not None
    assert components["offensive_ratio"].raw_value is not None
    assert components["synergy"].raw_value == NORMALIZED_PVPOKE_SCORE_FALLBACK
    assert components["role_fit"].raw_value == NORMALIZED_PVPOKE_SCORE_FALLBACK
    assert ("bait_dependence_proxy", 0.0) in components["consistency"].diagnostics
    assert ("shield_fragility", 0.0) in components["safety"].diagnostics
    assert ("pool_min", 100.0) in components["bulk"].diagnostics
    assert ("neutral_fallback", True) in components["synergy"].diagnostics
    assert ("neutral_fallback", True) in components["role_fit"].diagnostics


def test_ranking_aware_roster_score_uses_type_ratio_multiplication_and_weighting() -> None:
    type_effectiveness = {
        "electric": {"water": 1.6, "flying": 1.6, "fire": 1.0, "grass": 0.625},
        "flying": {"water": 1.0, "flying": 1.0, "fire": 1.0, "grass": 1.6},
        "water": {"water": 0.625, "flying": 1.0, "fire": 1.6, "grass": 0.625},
    }

    score = calculate_ranking_aware_roster_score(
        team_indices=[0, 1],
        matrices=[[[620], [620]]] * 3,
        bulk_by_row=[100.0, 100.0],
        pokemon_types_by_row=[("fire",), ("grass",)],
        move_types_by_row=[("electric",), ("water",)],
        opponent_types_by_col=[("water", "flying")],
        type_effectiveness=type_effectiveness,
        top_threat_indices=(0,),
        full_meta_indices=(0,),
    )

    components = {component.name: component for component in score.components}
    assert components["defensive_ratio"].raw_value == pytest.approx(0.3)
    assert components["offensive_ratio"].raw_value == pytest.approx(1.0)


def test_ranking_aware_roster_score_rejects_invalid_threat_indices() -> None:
    with pytest.raises(ValueError, match="threat indices"):
        calculate_ranking_aware_roster_score(
            team_indices=[0],
            matrices=[[[620]]],
            bulk_by_row=[100.0],
            top_threat_indices=(-1,),
            full_meta_indices=(0,),
        )


def test_ranking_aware_roster_score_treats_invalid_type_multipliers_as_neutral() -> None:
    score = calculate_ranking_aware_roster_score(
        team_indices=[0],
        matrices=[[[620]]],
        bulk_by_row=[100.0],
        move_types_by_row=[("water",)],
        opponent_types_by_col=[("fire",)],
        type_effectiveness={"water": {"fire": float("nan")}},
        top_threat_indices=(0,),
        full_meta_indices=(0,),
    )

    components = {component.name: component for component in score.components}
    assert components["offensive_ratio"].raw_value == pytest.approx((1.0 - 0.39) / (1.6 - 0.39))


def test_ranking_aware_roster_score_uses_neutral_type_ratio_fallbacks() -> None:
    score = calculate_ranking_aware_roster_score(
        team_indices=[0, 1, 2],
        matrices=[[[620], [620], [620]]] * 3,
        bulk_by_row=[100.0, 100.0, 100.0],
        top_threat_indices=(0,),
        full_meta_indices=(0,),
    )

    components = {component.name: component for component in score.components}
    assert components["defensive_ratio"].raw_value == 0.5
    assert components["offensive_ratio"].raw_value == 0.5
    assert ("missing_type_data", True) in components["defensive_ratio"].diagnostics
    assert ("missing_move_or_type_data", True) in components["offensive_ratio"].diagnostics


def test_weighted_roster_score_allows_component_tradeoffs() -> None:
    matrices = [
        [[620, 620], [620, 620], [620, 620], [620, 620], [620, 620], [620, 620]],
        [[620, 620], [620, 620], [620, 620], [620, 620], [620, 620], [620, 620]],
        [[620, 620], [620, 620], [620, 620], [620, 620], [620, 620], [620, 620]],
    ]

    safer_team = calculate_ranking_aware_roster_score(
        team_indices=[0, 1, 2],
        matrices=matrices,
        bulk_by_row=[190.0, 190.0, 190.0, 100.0, 100.0, 100.0],
        safety_by_row=[0.9, 0.9, 0.9, 0.2, 0.2, 0.2],
        consistency_by_row=[0.9, 0.9, 0.9, 0.3, 0.3, 0.3],
        top_threat_indices=(0,),
        full_meta_indices=(0, 1),
    )
    fragile_team = calculate_ranking_aware_roster_score(
        team_indices=[3, 4, 5],
        matrices=matrices,
        bulk_by_row=[190.0, 190.0, 190.0, 100.0, 100.0, 100.0],
        safety_by_row=[0.9, 0.9, 0.9, 0.2, 0.2, 0.2],
        consistency_by_row=[0.9, 0.9, 0.9, 0.3, 0.3, 0.3],
        top_threat_indices=(0,),
        full_meta_indices=(0, 1),
    )

    assert safer_team.final_score > fragile_team.final_score
