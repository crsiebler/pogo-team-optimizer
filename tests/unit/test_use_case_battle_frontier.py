from pogo_team_optimizer.application.use_case import AnalyzeMetaUseCase


class FakeSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        return (
            ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon", "Gmon", "Hmon"],
            ["Opp1", "Opp2"],
            [
                [
                    [900, 400],
                    [400, 900],
                    [700, 700],
                    [680, 680],
                    [660, 660],
                    [640, 640],
                    [620, 620],
                    [610, 610],
                ]
            ],
        )


class LineupBattleFrontierSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]
        cols = ["Opp1"]
        matrix = [
            [650],
            [640],
            [630],
            [300],
            [300],
            [300],
        ]
        return rows, cols, [matrix, matrix, matrix]


class WeakLineupBattleFrontierSimulationRepository:
    def load(self) -> tuple[list[str], list[str], list[list[list[int]]]]:
        rows = ["Amon", "Bmon", "Cmon", "Dmon", "Emon", "Fmon"]
        cols = ["Opp1"]
        matrix = [[300] for _ in rows]
        return rows, cols, [matrix, matrix, matrix]


class FakePokemonRepository:
    def get_types(self, species_name: str) -> tuple[str, ...]:
        return ("normal",)

    def get_base_stats(self, species_name: str) -> tuple[int, int, int] | None:
        return (100, 100, 100)


class FakeBattleFrontierPointsRepository:
    def __init__(self, points_by_species: dict[str, int]) -> None:
        self.points_by_species = points_by_species

    def get_points(self, species_name: str) -> int:
        return self.points_by_species.get(species_name, 0)


def test_use_case_enforces_bfmaster_legality_rules() -> None:
    use_case = AnalyzeMetaUseCase(
        simulation_repository=FakeSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
        battle_frontier_points_repository=FakeBattleFrontierPointsRepository(
            {
                "Amon": 5,
                "Bmon": 5,
                "Cmon": 3,
                "Dmon": 3,
                "Emon": 0,
                "Fmon": 0,
                "Gmon": 0,
                "Hmon": 0,
            }
        ),
    )

    result = use_case.execute(seed=7, restarts=40)

    team_species = {member["species"] for member in result["recommended_team"]["members"]}
    assert not {"Amon", "Bmon"}.issubset(team_species)
    assert (
        sum(
            use_case.battle_frontier_points_repository.get_points(member["species"])
            for member in result["recommended_team"]["members"]
        )
        <= 11
    )
    assert (
        sum(
            use_case.battle_frontier_points_repository.get_points(member["species"]) == 5
            for member in result["recommended_team"]["members"]
        )
        <= 1
    )


def test_use_case_reports_bfmaster_legality_metrics() -> None:
    use_case = AnalyzeMetaUseCase(
        simulation_repository=FakeSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
        battle_frontier_points_repository=FakeBattleFrontierPointsRepository(
            {
                "Amon": 5,
                "Bmon": 5,
                "Cmon": 3,
                "Dmon": 3,
                "Emon": 0,
                "Fmon": 0,
                "Gmon": 0,
                "Hmon": 0,
            }
        ),
    )

    result = use_case.execute(seed=7, restarts=40)

    metrics = result["recommended_team"]["metrics"]
    team_species = [member["species"] for member in result["recommended_team"]["members"]]

    assert metrics["battle_frontier_points_used"] == sum(
        use_case.battle_frontier_points_repository.get_points(species) for species in team_species
    )
    assert metrics["battle_frontier_five_point_members"] == sum(
        use_case.battle_frontier_points_repository.get_points(species) == 5
        for species in team_species
    )
    assert metrics["battle_frontier_mega_members"] == 0
    assert metrics["battle_frontier_max_points"] == 11
    assert metrics["battle_frontier_max_five_point_members"] == 1
    assert metrics["battle_frontier_max_mega_members"] == 1


def test_use_case_reports_battle_frontier_lineup_point_diagnostics() -> None:
    use_case = AnalyzeMetaUseCase(
        simulation_repository=LineupBattleFrontierSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
        battle_frontier_points_repository=FakeBattleFrontierPointsRepository(
            {
                "Amon": 0,
                "Bmon": 1,
                "Cmon": 3,
                "Dmon": 2,
                "Emon": 0,
                "Fmon": 1,
            }
        ),
    )

    result = use_case.execute(seed=7, restarts=1)

    metrics = result["recommended_team"]["metrics"]
    first_lineup = result["recommended_lineups"][0]
    assert metrics["battle_frontier_points_used"] == 7
    assert metrics["battle_frontier_free_low_point_usage_rate"] == 114 / (57 * 3)
    assert metrics["battle_frontier_high_point_usage_rate"] == 30 / (57 * 3)
    assert first_lineup["battle_frontier_points_used"] == 4


def test_use_case_reports_battle_frontier_bench_warnings() -> None:
    use_case = AnalyzeMetaUseCase(
        simulation_repository=WeakLineupBattleFrontierSimulationRepository(),
        pokemon_repository=FakePokemonRepository(),
        battle_frontier_points_repository=FakeBattleFrontierPointsRepository(
            {
                "Amon": 0,
                "Bmon": 1,
                "Cmon": 3,
                "Dmon": 2,
                "Emon": 0,
                "Fmon": 5,
            }
        ),
    )

    result = use_case.execute(seed=7, restarts=1)

    warnings_by_species = {
        entry["member"]["species"]: [warning["code"] for warning in entry["warnings"]]
        for entry in result["recommended_team"]["bench_utility"]
    }
    assert "expensive_mostly_bench" in warnings_by_species["Fmon"]
    assert "low_point_paper_coverage" in warnings_by_species["Emon"]
