from typing import Any

import pytest

from pogo_team_optimizer.application import use_case as use_case_module
from pogo_team_optimizer.application.use_case import AnalyzeMetaUseCase
from pogo_team_optimizer.domain.models import RankingCategory, RankingProfile, RankingRow


class FakePokemonRepository:
    def get_types(self, species_name: str) -> tuple[str, ...]:
        return ("normal",)

    def get_base_stats(self, species_name: str) -> tuple[int, int, int] | None:
        return (100, 100, 100)


class ShapePokemonRepository:
    def get_types(self, species_name: str) -> tuple[str, ...]:
        return {
            "Amon": ("water",),
            "Bmon": ("grass",),
            "Cmon": ("fire",),
            "Dmon": ("grass",),
            "Emon": ("water",),
            "Fmon": ("fighting",),
        }[species_name]

    def get_base_stats(self, species_name: str) -> tuple[int, int, int] | None:
        return (100, 100, 100)


class LineupSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]
        cols = ["Opp1", "Opp2"]
        matrix = [
            [650, 650],
            [640, 640],
            [630, 630],
            [620, 620],
            [610, 610],
            [600, 600],
        ]
        return rows, cols, [matrix, matrix, matrix]


class MissingMatchupSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int | None]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon", "Gmon"]
        cols = ["Opp1", "Opp2"]
        matrix = [[620, 620] for _ in rows]
        missing_matrix = [list(row) for row in matrix]
        missing_matrix[6][1] = None
        return rows, cols, [matrix, missing_matrix, matrix]


class TooFewCompleteMatchupsSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int | None]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]
        cols = ["Opp1", "Opp2"]
        matrix = [[620, 620] for _ in rows]
        missing_matrix = [list(row) for row in matrix]
        missing_matrix[5][0] = None
        return rows, cols, [matrix, missing_matrix, matrix]


class TieBreakSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = ["Zmon", "Amon", "Bmon", "Cmon", "Dmon", "Emon"]
        cols = ["Opp1"]
        matrix = [[600] for _ in rows]
        return rows, cols, [matrix, matrix, matrix]


class EqualResourceSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]
        cols = ["Opp1"]
        matrix = [[600] for _ in rows]
        return rows, cols, [matrix, matrix, matrix]


class BelowViabilitySimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]
        cols = ["Opp1"]
        matrix = [[490] for _ in rows]
        return rows, cols, [matrix, matrix, matrix]


class FakeRankingsRepository:
    def load(self) -> RankingProfile:
        overall_scores = {
            species: RankingRow(species, 100.0 - idx, normalized_score=1.0)
            for idx, species in enumerate(("Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"))
        }
        high_back_scores = {
            "Amon": RankingRow("Amon", 100.0, normalized_score=1.0),
            "Bmon": RankingRow("Bmon", 0.0, normalized_score=0.0),
            "Cmon": RankingRow("Cmon", 100.0, normalized_score=1.0),
            "Dmon": RankingRow("Dmon", 0.0, normalized_score=0.0),
            "Emon": RankingRow("Emon", 0.0, normalized_score=0.0),
            "Fmon": RankingRow("Fmon", 0.0, normalized_score=0.0),
        }
        return RankingProfile(
            scores_by_category={
                RankingCategory.OVERALL: overall_scores,
                RankingCategory.LEADS: {
                    "Amon": RankingRow("Amon", 0.0, normalized_score=0.0),
                    "Bmon": RankingRow("Bmon", 100.0, normalized_score=1.0),
                    "Cmon": RankingRow("Cmon", 0.0, normalized_score=0.0),
                    "Dmon": RankingRow("Dmon", 0.0, normalized_score=0.0),
                    "Emon": RankingRow("Emon", 0.0, normalized_score=0.0),
                    "Fmon": RankingRow("Fmon", 0.0, normalized_score=0.0),
                },
                RankingCategory.SWITCHES: high_back_scores,
                RankingCategory.CLOSERS: high_back_scores,
                RankingCategory.ATTACKERS: high_back_scores,
                RankingCategory.CHARGERS: high_back_scores,
                RankingCategory.CONSISTENCY: high_back_scores,
            }
        )


class RankedEligibilitySimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon", "Unrankedmon"]
        cols = ["Opp1"]
        matrix = [[620] for _ in rows]
        return rows, cols, [matrix, matrix, matrix]


class TooFewRankedCandidatesSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Unrankedmon"]
        cols = ["Opp1"]
        matrix = [[620] for _ in rows]
        return rows, cols, [matrix, matrix, matrix]


class NormalizedRankedEligibilitySimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = [
            "Charizard (Shadow) FireSpin+BlastBurn/DragonClaw 4/13/14",
            "Amon Tackle+BodySlam/HyperBeam 0/15/15",
            "Bmon VineWhip+PowerWhip/LeafBlade 1/14/14",
            "Cmon Ember+FlameCharge/BlastBurn 2/13/13",
            "Dmon Counter+CloseCombat/StoneEdge 3/12/12",
            "Emon WaterGun+Surf/HydroPump 4/11/11",
        ]
        cols = ["Opp1"]
        matrix = [[620] for _ in rows]
        return rows, cols, [matrix, matrix, matrix]


class OverallRankingsRepository:
    def __init__(self, ranked_species: tuple[str, ...] | list[str]) -> None:
        self.ranked_species = tuple(ranked_species)

    def load(self) -> RankingProfile:
        return RankingProfile(
            scores_by_category={
                RankingCategory.OVERALL: {
                    species: RankingRow(species, 100.0 - idx)
                    for idx, species in enumerate(self.ranked_species)
                }
            }
        )


class ThreatPoolSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]
        cols = ["TopOpp", "UnrankedOpp", "BroadOpp"]
        matrix = [[620, 300, 500] for _ in rows]
        return rows, cols, [matrix, matrix, matrix]


class NonRankingThreatFallbackSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]
        cols = ["EarlyOpp", "MiddleOpp", "LateThreat"]
        matrix = [[620, 620, 300] for _ in rows]
        return rows, cols, [matrix, matrix, matrix]


class ThreatPoolRankingsRepository:
    def __init__(self, scores: dict[str, float]) -> None:
        self.scores = scores

    def load(self) -> RankingProfile:
        overall_scores = {
            species: RankingRow(species, score) for species, score in self.scores.items()
        }
        for idx, species in enumerate(("Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon")):
            overall_scores.setdefault(species, RankingRow(species, 100.0 - idx))
        return RankingProfile(scores_by_category={RankingCategory.OVERALL: overall_scores})


class RoleOnlyRankingsRepository:
    def load(self) -> RankingProfile:
        return RankingProfile(
            scores_by_category={
                RankingCategory.SWITCHES: {
                    species: RankingRow(species, 100.0)
                    for species in ("Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon")
                }
            }
        )


class SynergyTypeEffectivenessRepository:
    def load(self) -> dict[str, dict[str, float]]:
        return {
            "electric": {"water": 1.6, "flying": 1.6, "grass": 0.625, "fire": 1.0},
            "grass": {"water": 1.6, "flying": 0.625, "grass": 0.625, "fire": 0.625},
            "water": {"water": 0.625, "flying": 1.0, "grass": 0.625, "fire": 1.6},
            "fire": {"water": 0.625, "flying": 1.0, "grass": 1.6, "fire": 0.625},
            "flying": {"water": 1.0, "flying": 1.0, "grass": 1.6, "fire": 1.0},
        }


class RankingAwareSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = [
            "Watermon WaterGun+Surf/HydroPump",
            "Grassmon VineWhip+PowerWhip/LeafBlade",
            "Firemon Ember+FlameCharge/BlastBurn",
            "Electricmon ThunderShock+WildCharge/Thunderbolt",
            "Flymon WingAttack+SkyAttack/BraveBird",
            "Rockmon SmackDown+RockSlide/StoneEdge",
        ]
        cols = ["WaterOpp", "FlyingOpp"]
        matrix = [[600, 600] for _ in rows]
        return rows, cols, [matrix, matrix, matrix]


class RankingAwarePokemonRepository:
    def __init__(self) -> None:
        self.type_queries: list[str] = []

    def get_types(self, species_name: str) -> tuple[str, ...]:
        self.type_queries.append(species_name)
        return {
            "Watermon": ("water",),
            "Grassmon": ("grass",),
            "Firemon": ("fire",),
            "Electricmon": ("electric",),
            "Flymon": ("flying",),
            "Rockmon": ("rock",),
            "WaterOpp": ("water",),
            "FlyingOpp": ("flying",),
        }[species_name]

    def get_base_stats(self, species_name: str) -> tuple[int, int, int] | None:
        return (100, 100, 100)


class RankingAwarePokemonRepositoryWithoutOpponentTypes(RankingAwarePokemonRepository):
    def get_types(self, species_name: str) -> tuple[str, ...]:
        if species_name in {"WaterOpp", "FlyingOpp"}:
            self.type_queries.append(species_name)
            raise KeyError(species_name)
        return super().get_types(species_name)


class RankingAwareMoveRepository:
    def get_move_type(self, move_name: str) -> str | None:
        return {
            "WaterGun": "water",
            "Surf": "water",
            "HydroPump": "water",
            "VineWhip": "grass",
            "PowerWhip": "grass",
            "LeafBlade": "grass",
            "Ember": "fire",
            "FlameCharge": "fire",
            "BlastBurn": "fire",
            "ThunderShock": "electric",
            "WildCharge": "electric",
            "Thunderbolt": "electric",
            "WingAttack": "flying",
            "SkyAttack": "flying",
            "BraveBird": "flying",
            "SmackDown": "rock",
            "RockSlide": "rock",
            "StoneEdge": "rock",
        }.get(move_name)


class RankingAwareTypeEffectivenessRepository:
    def load(self) -> dict[str, dict[str, float]]:
        return {
            "water": {
                "water": 0.625,
                "flying": 1.0,
                "electric": 1.0,
                "grass": 0.625,
                "fire": 1.6,
                "rock": 1.6,
            },
            "grass": {
                "water": 1.6,
                "flying": 0.625,
                "electric": 1.0,
                "grass": 0.625,
                "fire": 0.625,
                "rock": 1.6,
            },
            "fire": {
                "water": 0.625,
                "flying": 1.0,
                "electric": 1.0,
                "grass": 1.6,
                "fire": 0.625,
                "rock": 0.625,
            },
            "electric": {
                "water": 1.6,
                "flying": 1.6,
                "electric": 0.625,
                "grass": 0.625,
                "fire": 1.0,
                "rock": 1.0,
            },
            "flying": {
                "water": 1.0,
                "flying": 1.0,
                "electric": 0.625,
                "grass": 1.6,
                "fire": 1.0,
                "rock": 0.625,
            },
            "rock": {
                "water": 1.0,
                "flying": 1.6,
                "electric": 1.0,
                "grass": 1.0,
                "fire": 1.6,
                "rock": 1.0,
            },
        }


def test_use_case_exposes_structured_recommended_lineups() -> None:
    result = AnalyzeMetaUseCase(
        simulation_repository=LineupSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1)

    lineups = result["recommended_lineups"]

    assert len(lineups) == 5
    first = lineups[0]
    assert first["lead"]["species"] == "Amon"
    assert [member["species"] for member in first["back_pair"]] == ["Bmon", "Cmon"]
    assert first["team_shape"] == "unclassified"
    assert first["lineup_score"] == 650.0
    assert first["score_summary"] == {
        "mean_score": 650.0,
        "dominating_matchups": 6,
        "overwhelming_matchups": 0,
    }
    assert first["resource_paths"] == [
        {
            "name": "balanced",
            "lead_shield": 1,
            "back_shield": 1,
            "mean_best_score": 650.0,
            "dominating_matchups": 2,
            "overwhelming_matchups": 0,
        },
        {
            "name": "shield_spend",
            "lead_shield": 2,
            "back_shield": 0,
            "mean_best_score": 650.0,
            "dominating_matchups": 2,
            "overwhelming_matchups": 0,
        },
        {
            "name": "shield_save",
            "lead_shield": 0,
            "back_shield": 2,
            "mean_best_score": 650.0,
            "dominating_matchups": 2,
            "overwhelming_matchups": 0,
        },
    ]


def test_use_case_filters_rows_with_missing_matchups_before_optimization() -> None:
    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=MissingMatchupSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1)

    selected_species = {member["species"] for member in result["recommended_team"]["members"]}

    assert selected_species == {"Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"}
    assert "Gmon" not in selected_species


def test_use_case_fails_when_missing_matchups_leave_too_few_candidates() -> None:
    with pytest.raises(ValueError, match="Only 5 eligible candidates remain") as exc_info:
        AnalyzeMetaUseCase(
            simulation_repository=TooFewCompleteMatchupsSimulationRepository(),
            pokemon_repository=FakePokemonRepository(),
        ).execute(seed=7, restarts=1)

    assert "missing matchup data" in str(exc_info.value)
    assert "at least 6 are required" in str(exc_info.value)


def test_use_case_filters_unranked_candidates_before_optimization() -> None:
    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=RankedEligibilitySimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
        rankings_repository=OverallRankingsRepository(
            ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]
        ),
    ).execute(seed=7, restarts=1)

    selected_species = {member["species"] for member in result["recommended_team"]["members"]}

    assert selected_species == {"Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"}
    assert "Unrankedmon" not in selected_species


def test_use_case_fails_when_overall_rankings_leave_too_few_candidates() -> None:
    with pytest.raises(ValueError, match="Only 5 eligible candidates remain") as exc_info:
        AnalyzeMetaUseCase(
            simulation_repository=TooFewRankedCandidatesSimulationRepository(),
            pokemon_repository=FakePokemonRepository(),
            rankings_repository=OverallRankingsRepository(
                ["Amon", "Bmon", "Cmon", "Dmon", "Emon"]
            ),
        ).execute(seed=7, restarts=1)

    assert "active overall rankings" in str(exc_info.value)
    assert "at least 6 are required" in str(exc_info.value)


def test_use_case_requires_overall_rankings_not_role_rankings_for_eligibility() -> None:
    with pytest.raises(ValueError, match="Only 0 eligible candidates remain") as exc_info:
        AnalyzeMetaUseCase(
            simulation_repository=LineupSimulationRepository(),
            pokemon_repository=FakePokemonRepository(),
            rankings_repository=RoleOnlyRankingsRepository(),
        ).execute(seed=7, restarts=1)

    assert "active overall rankings" in str(exc_info.value)


def test_use_case_normalizes_ranked_candidate_labels_for_eligibility() -> None:
    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=NormalizedRankedEligibilitySimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
        rankings_repository=OverallRankingsRepository(
            [
                "Charizard (Shadow) FireSpin+BlastBurn/DragonClaw 4/13/14",
                "Amon Tackle+BodySlam/HyperBeam 0/15/15",
                "Bmon VineWhip+PowerWhip/LeafBlade 1/14/14",
                "Cmon Ember+FlameCharge/BlastBurn 2/13/13",
                "Dmon Counter+CloseCombat/StoneEdge 3/12/12",
                "Emon WaterGun+Surf/HydroPump 4/11/11",
            ]
        ),
    ).execute(seed=7, restarts=1)

    selected_species = {member["species"] for member in result["recommended_team"]["members"]}

    assert "Charizard (Shadow)" in selected_species
    assert selected_species == {"Charizard (Shadow)", "Amon", "Bmon", "Cmon", "Dmon", "Emon"}


def test_use_case_wires_ranked_active_and_full_meta_threat_indices(monkeypatch: Any) -> None:
    captured: dict[str, list[int]] = {}

    class FakeOptimizer:
        def __init__(self, *_: object, **kwargs: object) -> None:
            captured["optimizer_top"] = list(kwargs["top_threat_indices"])
            captured["optimizer_full"] = list(kwargs["full_meta_indices"])

        def optimize(self, **_: object) -> object:
            class FakeSolution:
                member_indices = (0, 1, 2, 3, 4, 5)
                score = (
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    100.0,
                    60.0,
                    0.5,
                    0.0,
                    0.0,
                    600.0,
                    0.0,
                    0.0,
                    600.0,
                    620.0,
                    610.0,
                    60.0,
                    0.5,
                    0.5,
                    0.5,
                )

            return FakeSolution()

    original_roster_score = use_case_module.calculate_ranking_aware_roster_score

    def capture_roster_score(*args: object, **kwargs: object) -> object:
        captured["score_top"] = list(kwargs["top_threat_indices"])
        captured["score_full"] = list(kwargs["full_meta_indices"])
        return original_roster_score(*args, **kwargs)

    monkeypatch.setattr(use_case_module, "TeamOptimizer", FakeOptimizer)
    monkeypatch.setattr(
        use_case_module,
        "calculate_ranking_aware_roster_score",
        capture_roster_score,
    )

    result = AnalyzeMetaUseCase(
        simulation_repository=ThreatPoolSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
        rankings_repository=ThreatPoolRankingsRepository({"TopOpp": 99.0}),
        full_meta_rankings_repository=ThreatPoolRankingsRepository({"BroadOpp": 98.0}),
    ).execute(seed=7, restarts=1, top_threats=3)

    assert captured == {
        "optimizer_top": [0],
        "optimizer_full": [2],
        "score_top": [0],
        "score_full": [2],
    }
    assert {threat["opponent_label"] for threat in result["threats"]} <= {"TopOpp", "BroadOpp"}


def test_use_case_does_not_fall_back_full_meta_when_active_rankings_exist(
    monkeypatch: Any,
) -> None:
    captured: dict[str, list[int]] = {}

    class FakeOptimizer:
        def __init__(self, *_: object, **kwargs: object) -> None:
            captured["optimizer_top"] = list(kwargs["top_threat_indices"])
            captured["optimizer_full"] = list(kwargs["full_meta_indices"])

        def optimize(self, **_: object) -> object:
            class FakeSolution:
                member_indices = (0, 1, 2, 3, 4, 5)
                score = (
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    100.0,
                    60.0,
                    0.5,
                    0.0,
                    0.0,
                    600.0,
                    0.0,
                    0.0,
                    600.0,
                    620.0,
                    610.0,
                    60.0,
                    0.5,
                    0.5,
                    0.5,
                )

            return FakeSolution()

    original_roster_score = use_case_module.calculate_ranking_aware_roster_score

    def capture_roster_score(*args: object, **kwargs: object) -> object:
        captured["score_top"] = list(kwargs["top_threat_indices"])
        captured["score_full"] = list(kwargs["full_meta_indices"])
        return original_roster_score(*args, **kwargs)

    monkeypatch.setattr(use_case_module, "TeamOptimizer", FakeOptimizer)
    monkeypatch.setattr(
        use_case_module,
        "calculate_ranking_aware_roster_score",
        capture_roster_score,
    )

    result = AnalyzeMetaUseCase(
        simulation_repository=ThreatPoolSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
        rankings_repository=ThreatPoolRankingsRepository({"TopOpp": 99.0}),
    ).execute(seed=7, restarts=1, top_threats=3)

    assert captured == {
        "optimizer_top": [0],
        "optimizer_full": [],
        "score_top": [0],
        "score_full": [],
    }
    assert {threat["opponent_label"] for threat in result["threats"]} <= {"TopOpp"}


def test_use_case_preserves_all_target_threat_fallback_without_rankings() -> None:
    result = AnalyzeMetaUseCase(
        simulation_repository=NonRankingThreatFallbackSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1, top_threats=1)

    assert [threat["opponent_label"] for threat in result["threats"]] == ["LateThreat"]


def test_use_case_limits_recommended_lineups_from_argument() -> None:
    result = AnalyzeMetaUseCase(
        simulation_repository=LineupSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1, top_lineups=3)

    assert len(result["recommended_lineups"]) == 3
    assert result["safe_cores"] == []


def test_recommended_lineups_use_deterministic_index_tie_breaking() -> None:
    result = AnalyzeMetaUseCase(
        simulation_repository=TieBreakSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1)

    actual_order = [
        (lineup["lead"]["index"], tuple(member["index"] for member in lineup["back_pair"]))
        for lineup in result["recommended_lineups"][:5]
    ]

    assert actual_order == [
        (0, (1, 2)),
        (0, (1, 3)),
        (0, (1, 4)),
        (0, (1, 5)),
        (0, (2, 3)),
    ]


def test_recommended_lineups_use_role_fit_to_rank_similar_lineups() -> None:
    result = AnalyzeMetaUseCase(
        simulation_repository=EqualResourceSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
        rankings_repository=FakeRankingsRepository(),
    ).execute(seed=7, restarts=1)

    first = result["recommended_lineups"][0]

    assert first["lead"]["species"] == "Bmon"
    assert [member["species"] for member in first["back_pair"]] == ["Amon", "Cmon"]
    assert first["score_summary"]["resource_mean_score"] == 600.0
    assert first["score_summary"]["role_fit_score"] == 1.0
    assert first["lineup_score"] == 612.0


def test_role_fit_does_not_make_resource_poor_lineups_viable() -> None:
    result = AnalyzeMetaUseCase(
        simulation_repository=BelowViabilitySimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
        rankings_repository=FakeRankingsRepository(),
    ).execute(seed=7, restarts=1)

    assert result["recommended_lineups"] == []


def test_recommended_lineups_include_synergy_score_when_type_data_is_available() -> None:
    result = AnalyzeMetaUseCase(
        simulation_repository=EqualResourceSimulationRepository(),
        pokemon_repository=ShapePokemonRepository(),
        type_effectiveness_repository=SynergyTypeEffectivenessRepository(),
    ).execute(seed=7, restarts=1)

    first = result["recommended_lineups"][0]

    assert first["score_summary"]["resource_mean_score"] == 600.0
    assert first["score_summary"]["synergy_score"] > 0.0
    assert first["lineup_score"] != first["score_summary"]["resource_mean_score"]


def test_recommended_lineups_filter_below_threshold_blended_synergy_scores() -> None:
    row_labels = ["Amon", "Bmon", "Cmon"]
    matrices = [
        [[350], [501], [350]],
        [[350], [501], [350]],
        [[350], [501], [350]],
    ]

    lineups = use_case_module._build_recommended_lineups(
        row_labels=row_labels,
        matrices=matrices,
        team_indices=(0, 1, 2),
        species_cache={"Amon": ("water",), "Bmon": ("grass",), "Cmon": ("water", "flying")},
        species_by_row=row_labels,
        pokemon_types_by_row=[("water",), ("grass",), ("water", "flying")],
        type_effectiveness=SynergyTypeEffectivenessRepository().load(),
        threat_weights=[1.0],
    )

    assert [lineup["lead"]["index"] for lineup in lineups] == [1]
    assert all(lineup["lineup_score"] >= 500.0 for lineup in lineups)


def test_shape_classification_does_not_change_lineup_score_or_order() -> None:
    baseline_result = AnalyzeMetaUseCase(
        simulation_repository=LineupSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1)
    result = AnalyzeMetaUseCase(
        simulation_repository=LineupSimulationRepository(),
        pokemon_repository=ShapePokemonRepository(),
    ).execute(seed=7, restarts=1)

    baseline_lineups = baseline_result["recommended_lineups"]
    lineups = result["recommended_lineups"]

    assert [
        (lineup["lead"]["index"], tuple(member["index"] for member in lineup["back_pair"]))
        for lineup in lineups[:3]
    ] == [
        (lineup["lead"]["index"], tuple(member["index"] for member in lineup["back_pair"]))
        for lineup in baseline_lineups[:3]
    ]
    assert [lineup["lineup_score"] for lineup in lineups[:3]] == [
        lineup["lineup_score"] for lineup in baseline_lineups[:3]
    ]
    assert result["recommended_team"]["score"] == baseline_result["recommended_team"]["score"]
    assert [lineup["team_shape"] for lineup in lineups[:3]] == ["ABC", "ABB", "ABA"]


def test_lineup_metrics_are_distinguished_from_legacy_full_roster_metrics() -> None:
    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=LineupSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1)

    metrics = result["recommended_team"]["metrics"]

    assert metrics["lineup_objective_score"] > 0
    assert metrics["lineup_best_score"] == 650.0
    assert metrics["lineup_top_n_mean_score"] > 0
    assert metrics["lineup_viable_count"] >= 3
    assert metrics["legacy_full_roster_mean_best_score"] == metrics["mean_best_score"]
    assert metrics["legacy_full_roster_dominate_count"] == metrics["dominate_count"]
    assert metrics["legacy_full_roster_overwhelming_count"] == metrics["overwhelming_count"]


def test_use_case_skips_non_actionable_bench_utility_diagnostics() -> None:
    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=LineupSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1)

    assert result["recommended_team"]["bench_utility"] == []


def test_use_case_does_not_compute_normal_bench_utility(monkeypatch: Any) -> None:
    def fail_bench_utility_scoring(*args: object, **kwargs: object) -> None:
        raise AssertionError("bench utility scoring should be skipped for normal results")

    monkeypatch.setattr(
        use_case_module,
        "score_roster_bench_utility",
        fail_bench_utility_scoring,
    )

    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=LineupSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1)

    assert result["recommended_team"]["bench_utility"] == []


def test_use_case_skips_normal_bench_utility_warnings() -> None:
    class WeakSimulationRepository:
        def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
            rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]
            cols = ["Opp1"]
            matrix = [[300] for _ in rows]
            return rows, cols, [matrix, matrix, matrix]

    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=WeakSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1)

    assert result["recommended_team"]["bench_utility"] == []


def test_non_battle_frontier_results_omit_battle_frontier_diagnostics() -> None:
    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=LineupSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
    ).execute(seed=7, restarts=1)

    metrics = result["recommended_team"]["metrics"]
    first_lineup = result["recommended_lineups"][0]
    warnings = [
        warning
        for entry in result["recommended_team"]["bench_utility"]
        for warning in entry["warnings"]
    ]

    assert "battle_frontier_free_low_point_usage_rate" not in metrics
    assert "battle_frontier_high_point_usage_rate" not in metrics
    assert "battle_frontier_points_used" not in first_lineup
    assert all(warning["category"] != "battle_frontier" for warning in warnings)


def test_use_case_wires_opponent_column_types_into_ranking_aware_score() -> None:
    pokemon_repository = RankingAwarePokemonRepository()
    baseline_repository = RankingAwarePokemonRepositoryWithoutOpponentTypes()

    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=RankingAwareSimulationRepository(),
        pokemon_repository=pokemon_repository,
        move_repository=RankingAwareMoveRepository(),
        type_effectiveness_repository=RankingAwareTypeEffectivenessRepository(),
    ).execute(seed=7, restarts=1)
    baseline_result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=RankingAwareSimulationRepository(),
        pokemon_repository=baseline_repository,
        move_repository=RankingAwareMoveRepository(),
        type_effectiveness_repository=RankingAwareTypeEffectivenessRepository(),
    ).execute(seed=7, restarts=1)

    metrics = result["recommended_team"]["metrics"]
    baseline_metrics = baseline_result["recommended_team"]["metrics"]

    assert {"WaterOpp", "FlyingOpp"}.issubset(set(pokemon_repository.type_queries))
    assert {"WaterOpp", "FlyingOpp"}.issubset(set(baseline_repository.type_queries))
    assert metrics["defensive_type_score"] != 0.0
    assert metrics["offensive_move_score"] != 0.0
    assert metrics["ranking_aware_score"] != baseline_metrics["ranking_aware_score"]


def test_use_case_exposes_ranking_aware_score_breakdown_and_diagnostics() -> None:
    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=RankingAwareSimulationRepository(),
        pokemon_repository=RankingAwarePokemonRepository(),
        move_repository=RankingAwareMoveRepository(),
        type_effectiveness_repository=RankingAwareTypeEffectivenessRepository(),
    ).execute(seed=7, restarts=1)

    team = result["recommended_team"]
    score_breakdown = team["score_breakdown"]
    diagnostics = team["ranking_diagnostics"]
    metrics = team["metrics"]

    assert score_breakdown["final_score"] == metrics["ranking_aware_score"]
    assert metrics["coverage_grade"] in {"A", "B", "C", "D", "F"}
    assert metrics["bulk_grade"] in {"A", "B", "C", "D", "F"}
    assert metrics["safety_grade"] in {"A", "B", "C", "D", "F"}
    assert metrics["consistency_grade"] in {"A", "B", "C", "D", "F"}
    assert isinstance(metrics["threat_score"], float)
    assert metrics["threat_score"] >= 0.0
    assert [component["name"] for component in score_breakdown["components"]] == [
        "synergy",
        "threat_coverage",
        "safety",
        "consistency",
        "bulk",
        "defensive_ratio",
        "offensive_ratio",
        "role_fit",
    ]
    assert diagnostics["key_covered_threats"]
    assert diagnostics["remaining_threats"] == []
    assert diagnostics["no_answer_threats"] == []
    assert diagnostics["single_answer_threats"] == []
    assert diagnostics["role_assumptions"] == [
        "Leads use PvPoke leads rankings when available.",
        "Back pairs use unordered PvPoke switches, closers, attackers, chargers, and consistency blends when available.",
    ]
    assert diagnostics["lineup_dependency"]["dependent"] is False


def test_recommended_lineups_expose_weighted_components_and_shared_weaknesses() -> None:
    result: dict[str, Any] = AnalyzeMetaUseCase(
        simulation_repository=EqualResourceSimulationRepository(),
        pokemon_repository=ShapePokemonRepository(),
        rankings_repository=FakeRankingsRepository(),
        type_effectiveness_repository=SynergyTypeEffectivenessRepository(),
    ).execute(seed=7, restarts=1)

    first = result["recommended_lineups"][0]

    assert first["score_breakdown"] == {
        "final_score": first["lineup_score"],
        "components": [
            {
                "name": "resource_path",
                "raw_value": first["score_summary"]["resource_mean_score"],
                "weight": 0.9,
                "weighted_score": first["score_summary"]["resource_mean_score"] * 0.9,
            },
            {
                "name": "role_fit",
                "raw_value": first["score_summary"]["role_fit_score"] * 1000.0,
                "weight": 0.03,
                "weighted_score": first["score_summary"]["role_fit_score"] * 30.0,
            },
            {
                "name": "synergy",
                "raw_value": first["score_summary"]["synergy_score"] * 1000.0,
                "weight": 0.07,
                "weighted_score": first["score_summary"]["synergy_score"] * 1000.0 * 0.07,
            },
        ],
    }
    assert first["ranking_diagnostics"]["role_assumptions"]
    assert any(
        lineup["ranking_diagnostics"]["shared_weaknesses"]
        for lineup in result["recommended_lineups"]
    )


def test_ranking_diagnostics_identify_lineup_dependency() -> None:
    row_labels = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]

    diagnostics = use_case_module._build_ranking_diagnostics(
        row_labels=row_labels,
        col_labels=["Opp1"],
        matrices=[
            [[620], [620], [620], [450], [450], [450]],
            [[620], [620], [620], [450], [450], [450]],
            [[620], [620], [620], [450], [450], [450]],
        ],
        metrics={
            "lineup_best_score": 620.0,
            "lineup_top_n_mean_score": 512.0,
            "lineup_viable_count": 1,
        },
        team_indices=(0, 1, 2, 3, 4, 5),
        pokemon_types_by_row=[("water",), ("grass",), ("fire",), ("normal",), ("normal",), ("normal",)],
        type_effectiveness=SynergyTypeEffectivenessRepository().load(),
        ranking_profile=None,
    )

    assert diagnostics["lineup_dependency"] == {
        "dependent": True,
        "reason": "Only one viable ordered lineup is available.",
        "best_lineup_score": 620.0,
        "top_lineup_mean_score": 512.0,
        "viable_lineup_count": 1,
    }


def test_ranking_diagnostics_classify_threat_level_answers_from_all_opponents() -> None:
    diagnostics = use_case_module._build_ranking_diagnostics(
        row_labels=["Amon", "Bmon", "Cmon"],
        col_labels=["CoveredOpp", "SingleOpp", "NoAnswerOpp"],
        matrices=[
            [
                [620, 620, 450],
                [610, 450, 450],
                [450, 450, 450],
            ],
            [
                [620, 450, 450],
                [610, 450, 450],
                [450, 450, 450],
            ],
            [
                [620, 450, 450],
                [610, 450, 450],
                [450, 450, 450],
            ],
        ],
        metrics={
            "lineup_best_score": 620.0,
            "lineup_top_n_mean_score": 620.0,
            "lineup_viable_count": 3,
        },
        team_indices=(0, 1, 2),
        pokemon_types_by_row=[("water",), ("grass",), ("fire",)],
        type_effectiveness=SynergyTypeEffectivenessRepository().load(),
        ranking_profile=None,
    )

    assert diagnostics["key_covered_threats"] == ["CoveredOpp"]
    assert diagnostics["single_answer_threats"] == ["SingleOpp"]
    assert diagnostics["no_answer_threats"] == ["NoAnswerOpp"]
    assert diagnostics["remaining_threats"] == ["NoAnswerOpp", "SingleOpp"]
