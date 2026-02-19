from pogo_team_optimizer.application.use_case import AnalyzeMetaUseCase
from pogo_team_optimizer.infrastructure.repositories.csv_matrix_repository import (
    CsvSimulationMatrixRepository,
)
from pogo_team_optimizer.infrastructure.repositories.pokemon_json_repository import (
    PokemonJsonRepository,
)


def test_use_case_returns_required_sections() -> None:
    use_case = AnalyzeMetaUseCase(
        simulation_repository=CsvSimulationMatrixRepository(
            [
                "data/simulations/crucible_0-shield.csv",
                "data/simulations/crucible_1-shield.csv",
                "data/simulations/crucible_2-shield.csv",
            ]
        ),
        pokemon_repository=PokemonJsonRepository("data/pokemon.json"),
    )

    result = use_case.execute(top_threats=5, top_cores=3, seed=7, restarts=10)

    assert "recommended_team" in result
    assert len(result["recommended_team"]["members"]) == 6
    assert len(result["coverage"]) == 3
    assert len(result["threats"]) == 5
    assert len(result["safe_cores"]) == 3
    assert len(result["target_map"]) > 0
