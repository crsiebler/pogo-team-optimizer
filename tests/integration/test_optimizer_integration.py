from pogo_team_optimizer.application.normalization import parse_base_species, parse_species
from pogo_team_optimizer.application.optimizer import TeamOptimizer
from pogo_team_optimizer.infrastructure.repositories.csv_matrix_repository import (
    CsvSimulationMatrixRepository,
)


def test_optimizer_returns_legal_team() -> None:
    repo = CsvSimulationMatrixRepository(
        [
            "data/simulations/great_0-shield.csv",
            "data/simulations/great_1-shield.csv",
            "data/simulations/great_2-shield.csv",
        ]
    )
    row_labels, col_labels, matrices = repo.load()
    optimizer = TeamOptimizer(
        row_labels,
        col_labels,
        matrices,
        bulk_by_row=[1.0] * len(row_labels),
        seed=7,
    )

    result = optimizer.optimize(restarts=10)
    assert len(result.member_indices) == 6

    bases = [parse_base_species(parse_species(row_labels[idx])) for idx in result.member_indices]
    assert len(set(bases)) == 6
