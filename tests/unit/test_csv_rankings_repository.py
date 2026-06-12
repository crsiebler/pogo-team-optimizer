from pogo_team_optimizer.domain.models import RankingCategory
from pogo_team_optimizer.infrastructure.repositories.csv_rankings_repository import (
    CsvRankingsRepository,
)


def test_csv_rankings_repository_loads_category_scores(tmp_path) -> None:
    leads = tmp_path / "leads.csv"
    switches = tmp_path / "switches.csv"
    leads.write_text(
        "Pokemon,Score,Dex\nCorviknight,94,823\nLickilicky,92.7,463\n",
        encoding="utf-8",
    )
    switches.write_text(
        "Pokemon,Score,Dex\nCorviknight,88.3,823\n",
        encoding="utf-8",
    )

    profile = CsvRankingsRepository(
        {
            RankingCategory.LEADS: str(leads),
            RankingCategory.SWITCHES: str(switches),
        }
    ).load()

    assert profile.get_score(RankingCategory.LEADS, "Corviknight") == 94.0
    assert profile.scores_by_category[RankingCategory.LEADS]["Corviknight"].normalized_score is None
    assert profile.get_score(RankingCategory.LEADS, "Lickilicky") == 92.7
    assert profile.get_score(RankingCategory.SWITCHES, "Corviknight") == 88.3


def test_csv_rankings_repository_normalizes_species_names(tmp_path) -> None:
    rankings = tmp_path / "overall.csv"
    rankings.write_text(
        "Pokemon,Score\nClodsire 0/14/13,95\nLickilicky L+BS,93\n",
        encoding="utf-8",
    )

    profile = CsvRankingsRepository({RankingCategory.OVERALL: str(rankings)}).load()

    assert profile.get_score(RankingCategory.OVERALL, "Clodsire") == 95.0
    assert profile.get_score(RankingCategory.OVERALL, "Lickilicky") == 93.0


def test_csv_rankings_repository_skips_malformed_rows_without_defaults(tmp_path) -> None:
    rankings = tmp_path / "consistency.csv"
    rankings.write_text(
        "Pokemon,Score\nCorviknight,not-a-number\n,95\nLickilicky,92\n",
        encoding="utf-8",
    )

    profile = CsvRankingsRepository({RankingCategory.CONSISTENCY: str(rankings)}).load()

    assert profile.get_score(RankingCategory.CONSISTENCY, "Corviknight") is None
    assert profile.get_score(RankingCategory.CONSISTENCY, "") is None
    assert profile.get_score(RankingCategory.CONSISTENCY, "Lickilicky") == 92.0


def test_csv_rankings_repository_rejects_unknown_category() -> None:
    try:
        CsvRankingsRepository({"unknown": "rankings.csv"})
    except ValueError as error:
        assert "Unsupported ranking category" in str(error)
    else:
        raise AssertionError("expected ValueError")
