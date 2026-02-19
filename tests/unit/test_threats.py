from pogo_team_optimizer.application.analyzers import build_threats


def test_build_threats_prioritizes_single_cover_context() -> None:
    row_labels = ["Amon", "Bmon"]
    col_labels = ["Opp1", "Opp2"]

    # Opp1: shield0 only Amon wins, shield1 both win, shield2 only Amon wins
    # Opp2: both win across all shields
    matrices = [
        [[520, 700], [400, 710]],
        [[610, 720], [650, 730]],
        [[530, 740], [480, 750]],
    ]

    threats = build_threats(row_labels, col_labels, matrices, (0, 1), top_n=5)
    assert threats[0]["opponent_label"] == "Opp1"
    assert threats[0]["single_cover_count"] == 2
    assert threats[0]["no_cover_count"] == 0
    assert len(threats[0]["fragile_shields"]) == 2
