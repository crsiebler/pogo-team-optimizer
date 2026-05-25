from pogo_team_optimizer.application.ranking_pools import build_ranking_pools
from pogo_team_optimizer.domain.models import RankingCategory, RankingProfile, RankingRow


def _profile(scores: dict[str, float]) -> RankingProfile:
    return RankingProfile(
        scores_by_category={
            RankingCategory.OVERALL: {
                species: RankingRow(species=species, score=score)
                for species, score in scores.items()
            }
        }
    )


def test_build_ranking_pools_aligns_rankings_to_matrix_labels() -> None:
    pools = build_ranking_pools(
        active_profile=_profile({"Clodsire": 95.0}),
        full_meta_profile=None,
        row_labels=["Clodsire 0/14/13"],
        col_labels=["Clodsire 0/14/13"],
        top_threat_count=1,
    )

    assert pools.active_meta[0].species == "Clodsire"
    assert pools.active_meta[0].ranking_score == 95.0
    assert pools.active_meta[0].matrix_index == 0


def test_build_ranking_pools_prefers_column_labels_when_rows_differ() -> None:
    pools = build_ranking_pools(
        active_profile=_profile({"Clodsire": 95.0, "Lickilicky": 93.0}),
        full_meta_profile=None,
        row_labels=["Lickilicky"],
        col_labels=["Clodsire"],
        top_threat_count=1,
    )

    assert [entry.species for entry in pools.active_meta] == ["Clodsire"]
    assert pools.active_meta[0].matrix_index == 0


def test_build_ranking_pools_falls_back_to_row_labels_when_columns_are_empty() -> None:
    pools = build_ranking_pools(
        active_profile=_profile({"Lickilicky": 93.0}),
        full_meta_profile=None,
        row_labels=["Lickilicky"],
        col_labels=[],
        top_threat_count=1,
    )

    assert [entry.species for entry in pools.active_meta] == ["Lickilicky"]
    assert pools.active_meta[0].matrix_index == 0


def test_build_ranking_pools_keeps_missing_rankings_deterministic() -> None:
    pools = build_ranking_pools(
        active_profile=_profile({"Clodsire": 95.0}),
        full_meta_profile=None,
        row_labels=["Unknownmon", "Clodsire"],
        col_labels=["Unknownmon", "Clodsire"],
        top_threat_count=2,
    )

    assert [entry.species for entry in pools.active_meta] == ["Clodsire", "Unknownmon"]
    assert pools.active_meta[1].ranking_score is None


def test_build_ranking_pools_deduplicates_normalized_species_by_column_order() -> None:
    pools = build_ranking_pools(
        active_profile=_profile({"Clodsire": 95.0}),
        full_meta_profile=None,
        row_labels=["Clodsire 0/14/13", "Clodsire 1/15/14"],
        col_labels=["Clodsire 0/14/13", "Clodsire 1/15/14"],
        top_threat_count=2,
    )

    assert [entry.species for entry in pools.active_meta] == ["Clodsire"]
    assert pools.active_meta[0].label == "Clodsire 0/14/13"
    assert pools.active_meta[0].matrix_index == 0


def test_build_ranking_pools_deduplicates_base_species_like_optimizer() -> None:
    pools = build_ranking_pools(
        active_profile=_profile({"Dragonite": 90.0, "Dragonite (Shadow)": 92.0}),
        full_meta_profile=None,
        row_labels=["Dragonite", "Dragonite (Shadow)"],
        col_labels=["Dragonite", "Dragonite (Shadow)"],
        top_threat_count=2,
    )

    assert [entry.species for entry in pools.active_meta] == ["Dragonite (Shadow)"]
    assert pools.active_meta[0].base_species == "Dragonite"


def test_build_ranking_pools_orders_top_threats_and_normalizes_weights() -> None:
    pools = build_ranking_pools(
        active_profile=_profile({"Clodsire": 100.0, "Lickilicky": 90.0}),
        full_meta_profile=None,
        row_labels=["Unknownmon", "Lickilicky", "Clodsire"],
        col_labels=["Unknownmon", "Lickilicky", "Clodsire"],
        top_threat_count=2,
    )

    assert [entry.species for entry in pools.top_threats] == ["Clodsire", "Lickilicky"]
    assert [entry.weight for entry in pools.top_threats] == [100.0 / 190.0, 90.0 / 190.0]


def test_build_ranking_pools_uses_uniform_top_threat_weights_without_scores() -> None:
    pools = build_ranking_pools(
        active_profile=None,
        full_meta_profile=None,
        row_labels=["Clodsire", "Lickilicky", "Corviknight"],
        col_labels=["Clodsire", "Lickilicky", "Corviknight"],
        top_threat_count=2,
    )

    assert [entry.species for entry in pools.top_threats] == ["Clodsire", "Lickilicky"]
    assert [entry.weight for entry in pools.top_threats] == [0.5, 0.5]


def test_build_ranking_pools_treats_non_finite_scores_as_missing() -> None:
    pools = build_ranking_pools(
        active_profile=_profile({"Clodsire": float("inf"), "Lickilicky": 90.0}),
        full_meta_profile=None,
        row_labels=["Clodsire", "Lickilicky"],
        col_labels=["Clodsire", "Lickilicky"],
        top_threat_count=2,
    )

    assert [entry.species for entry in pools.top_threats] == ["Lickilicky", "Clodsire"]
    assert pools.top_threats[0].weight == 1.0
    assert pools.top_threats[1].ranking_score is None
    assert pools.top_threats[1].weight == 0.0


def test_build_ranking_pools_treats_out_of_range_scores_as_missing() -> None:
    pools = build_ranking_pools(
        active_profile=_profile(
            {"Clodsire": 101.0, "Corviknight": -1.0, "Lickilicky": 90.0}
        ),
        full_meta_profile=None,
        row_labels=["Clodsire", "Corviknight", "Lickilicky"],
        col_labels=["Clodsire", "Corviknight", "Lickilicky"],
        top_threat_count=3,
    )

    assert [entry.species for entry in pools.top_threats] == [
        "Lickilicky",
        "Clodsire",
        "Corviknight",
    ]
    assert pools.top_threats[0].weight == 1.0
    assert pools.top_threats[1].ranking_score is None
    assert pools.top_threats[1].weight == 0.0
    assert pools.top_threats[2].ranking_score is None
    assert pools.top_threats[2].weight == 0.0


def test_build_ranking_pools_builds_full_meta_pool_from_full_profile() -> None:
    pools = build_ranking_pools(
        active_profile=_profile({"Clodsire": 95.0}),
        full_meta_profile=_profile({"Lickilicky": 96.0, "Clodsire": 91.0}),
        row_labels=["Clodsire", "Lickilicky"],
        col_labels=["Clodsire", "Lickilicky"],
        top_threat_count=1,
    )

    assert [entry.species for entry in pools.active_meta] == ["Clodsire", "Lickilicky"]
    assert [entry.species for entry in pools.full_meta] == ["Lickilicky", "Clodsire"]
    assert pools.full_meta[0].ranking_score == 96.0
