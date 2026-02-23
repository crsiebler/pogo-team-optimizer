from pogo_team_optimizer.infrastructure.repositories.csv_switch_rankings_repository import (
    CsvSwitchRankingsRepository,
)


def test_switch_rankings_repository_reads_scores(tmp_path) -> None:
    rankings = tmp_path / "switches.csv"
    rankings.write_text(
        "Pokemon,Score\nCorviknight,94\nLickilicky,92.7\n",
        encoding="utf-8",
    )

    repository = CsvSwitchRankingsRepository(str(rankings))

    assert repository.get_switch_score("Corviknight") == 94.0
    assert repository.get_switch_score("Lickilicky") == 92.7


def test_switch_rankings_repository_returns_none_for_missing_species(tmp_path) -> None:
    rankings = tmp_path / "switches.csv"
    rankings.write_text("Pokemon,Score\nCorviknight,94\n", encoding="utf-8")

    repository = CsvSwitchRankingsRepository(str(rankings))

    assert repository.get_switch_score("Talonflame") is None
