from typing import Any

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


class SynergyTypeEffectivenessRepository:
    def load(self) -> dict[str, dict[str, float]]:
        return {
            "electric": {"water": 1.6, "flying": 1.6, "grass": 0.625, "fire": 1.0},
            "grass": {"water": 1.6, "flying": 0.625, "grass": 0.625, "fire": 0.625},
            "water": {"water": 0.625, "flying": 1.0, "grass": 0.625, "fire": 1.6},
            "fire": {"water": 0.625, "flying": 1.0, "grass": 1.6, "fire": 0.625},
            "flying": {"water": 1.0, "flying": 1.0, "grass": 1.6, "fire": 1.0},
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
