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
