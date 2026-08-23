from pogo_team_optimizer.application.analyzers import build_core_role_recommendation


def test_core_role_recommendation_orders_lead_switch_closer() -> None:
    row_labels = ["Leadmon", "Switchmon", "Closermon"]
    col_labels = ["Opp1", "Opp2", "Opp3"]
    matrices = [
        [
            [520, 500, 500],
            [510, 510, 510],
            [760, 760, 760],
        ],
        [
            [760, 760, 760],
            [530, 530, 530],
            [500, 500, 500],
        ],
        [
            [520, 520, 520],
            [510, 510, 510],
            [500, 500, 500],
        ],
    ]

    recommendation = build_core_role_recommendation(
        row_labels=row_labels,
        col_labels=col_labels,
        matrices=matrices,
        core_indices=(0, 1, 2),
        safety_by_row=[50.0, 95.0, 60.0],
    )

    assert recommendation["strategy"] == "ABC"
    assert recommendation["recommended_order"] == [
        {"role": "lead", "label": "Leadmon", "index": 0},
        {"role": "switch", "label": "Switchmon", "index": 1},
        {"role": "closer", "label": "Closermon", "index": 2},
    ]
    assert (
        recommendation["role_scores"]["Leadmon"]["lead"]
        > recommendation["role_scores"]["Leadmon"]["closer"]
    )
    assert (
        recommendation["role_scores"]["Switchmon"]["switch"]
        > recommendation["role_scores"]["Switchmon"]["lead"]
    )
    assert (
        recommendation["role_scores"]["Closermon"]["closer"]
        > recommendation["role_scores"]["Closermon"]["lead"]
    )


def test_core_role_recommendation_classifies_abb_shared_backline() -> None:
    row_labels = ["Countermon", "Mudmon", "Watermon"]
    col_labels = ["Flyer", "Steel", "Grass"]
    matrices = [
        [
            [740, 520, 740],
            [300, 740, 300],
            [320, 730, 320],
        ],
        [
            [740, 520, 740],
            [300, 740, 300],
            [320, 730, 320],
        ],
        [
            [740, 520, 740],
            [300, 740, 300],
            [320, 730, 320],
        ],
    ]

    recommendation = build_core_role_recommendation(
        row_labels=row_labels,
        col_labels=col_labels,
        matrices=matrices,
        core_indices=(0, 1, 2),
        safety_by_row=[55.0, 92.0, 75.0],
    )

    assert recommendation["strategy"] == "ABB"
    assert recommendation["recommended_order"][0]["label"] == "Countermon"
    assert recommendation["shared_weaknesses"] == ["Flyer", "Grass"]
    assert "gameplan_note" not in recommendation
