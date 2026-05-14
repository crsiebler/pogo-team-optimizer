from zipfile import ZipFile

from pogo_team_optimizer.infrastructure.exporters.csv_exporter import CsvExporter
from pogo_team_optimizer.infrastructure.exporters.excel_exporter import ExcelExporter
from pogo_team_optimizer.infrastructure.exporters.json_exporter import JsonExporter
from pogo_team_optimizer.infrastructure.exporters.markdown_exporter import MarkdownExporter
from pogo_team_optimizer.infrastructure.exporters.text_exporter import TextExporter


def build_result() -> dict[str, object]:
    return {
        "meta": "bfmaster",
        "recommended_team": {
            "members": [
                {"label": "Mewtwo", "types": ["psychic"]},
                {"label": "Gengar (Mega)", "types": ["ghost", "poison"]},
            ],
            "metrics": {
                "bulk_score": 100.0,
                "bulk_pool_min": 90.0,
                "bulk_pool_mean": 100.0,
                "bulk_pool_max": 110.0,
                "safety_score": 80.0,
                "safety_pool_min": 70.0,
                "safety_pool_mean": 80.0,
                "safety_pool_max": 90.0,
                "safety_priority": "medium",
                "safety_floor_target": 78.0,
                "safe_member_floor": 90.0,
                "safe_member_target": 1,
                "consistency_score": 610.0,
                "mean_best_score": 600.0,
                "redundant_coverage_2plus": 3,
                "redundant_coverage_3plus": 1,
                "single_cover_pairs": 2,
                "single_cover_rate": 0.25,
                "no_cover_pairs": 1,
                "no_cover_rate": 0.125,
                "dominate_count": 4,
                "dominate_rate": 0.5,
                "overwhelming_count": 0,
                "overwhelming_rate": 0.0,
                "total_pairs": 8,
                "battle_frontier_points_used": 8,
                "battle_frontier_five_point_members": 1,
                "battle_frontier_mega_members": 1,
                "battle_frontier_max_points": 11,
                "battle_frontier_max_five_point_members": 1,
                "battle_frontier_max_mega_members": 1,
            },
        },
        "coverage": [
            {"shield": 0, "wins": 1, "draws": 0, "losses": 1, "weighted_wins": 0.5},
        ],
        "safe_cores": [
            {
                "members": [{"label": "Mewtwo"}, {"label": "Gengar (Mega)"}, {"label": "Dialga"}],
                "strategy": "ABC",
                "recommended_order": [
                    {"role": "lead", "label": "Mewtwo", "index": 0},
                    {"role": "switch", "label": "Gengar (Mega)", "index": 1},
                    {"role": "closer", "label": "Dialga", "index": 2},
                ],
            }
        ],
        "threats": [
            {
                "opponent_label": "Zygarde",
                "single_cover_count": 1,
                "no_cover_count": 0,
                "fragile_shields": [
                    {
                        "shield": 0,
                        "winner_count": 1,
                        "only_answer": "Mewtwo",
                        "only_answer_score": 601,
                        "best_loser": None,
                        "best_loser_score": None,
                    }
                ],
                "shield_best_scores": [601],
            }
        ],
    }


def test_text_exporter_renders_battle_frontier_legality_metrics() -> None:
    rendered = TextExporter().export(build_result())

    assert rendered is not None
    assert "Battle Frontier legality" in rendered
    assert "points used: 8/11" in rendered
    assert "5-point members: 1/1" in rendered
    assert "Mega members: 1/1" in rendered


def test_text_exporter_renders_ordered_core_roles() -> None:
    rendered = TextExporter().export(build_result())

    assert rendered is not None
    assert "#1 ABC: Lead Mewtwo | Switch Gengar (Mega) | Closer Dialga" in rendered
    assert "use standard alignment" not in rendered


def test_markdown_exporter_renders_battle_frontier_legality_metrics() -> None:
    rendered = MarkdownExporter().export(build_result())

    assert rendered is not None
    assert "## Battle Frontier Legality" in rendered
    assert "- Points used: `8/11`" in rendered
    assert "- 5-point members: `1/1`" in rendered
    assert "- Mega members: `1/1`" in rendered


def test_markdown_exporter_renders_ordered_core_roles() -> None:
    rendered = MarkdownExporter().export(build_result())

    assert rendered is not None
    assert "**#1 ABC** Lead `Mewtwo` | Switch `Gengar (Mega)` | Closer `Dialga`" in rendered
    assert "use standard alignment" not in rendered


def test_existing_exporters_accept_results_with_battle_frontier_metrics(tmp_path) -> None:
    result = build_result()

    assert '"battle_frontier_points_used": 8' in JsonExporter().export(result)
    CsvExporter().export(result, output_path=str(tmp_path / "result.csv"))


def test_excel_exporter_writes_xlsx_workbook(tmp_path) -> None:
    output_path = tmp_path / "result.xlsx"

    ExcelExporter().export(build_result(), output_path=str(output_path))

    with ZipFile(output_path) as workbook:
        names = set(workbook.namelist())
        assert "[Content_Types].xml" in names
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        assert "xl/worksheets/sheet2.xml" in names
        first_sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")

    assert "Recommended Team" in first_sheet
    assert "Mewtwo" in first_sheet
