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
