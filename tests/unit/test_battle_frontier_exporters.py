import json
from copy import deepcopy
from csv import reader
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
            "bench_utility": [
                {
                    "member": {"label": "Mewtwo", "types": ["psychic"]},
                    "lineups_used": 12,
                    "lead_lineups_used": 5,
                    "back_lineups_used": 7,
                    "viable_lineup_rate": 0.8,
                    "all_lineup_rate": 0.2,
                    "best_lineup_score": 640.0,
                    "tier": "core",
                    "warnings": [],
                },
                {
                    "member": {"label": "Gengar (Mega)", "types": ["ghost", "poison"]},
                    "lineups_used": 1,
                    "lead_lineups_used": 0,
                    "back_lineups_used": 1,
                    "viable_lineup_rate": 0.05,
                    "all_lineup_rate": 0.0166666667,
                    "best_lineup_score": 525.0,
                    "tier": "low_utility",
                    "warnings": [
                        {
                            "category": "battle_frontier",
                            "code": "expensive_bench",
                            "severity": "warning",
                            "message": "Expensive Pokemon appears in few viable lineups.",
                        }
                    ],
                },
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
                "battle_frontier_free_low_point_usage_rate": 0.6666666667,
                "battle_frontier_high_point_usage_rate": 0.1754385965,
            },
            "score_breakdown": {
                "final_score": 0.74,
                "components": [
                    {
                        "name": "threat_coverage",
                        "raw_value": 0.8,
                        "weight": 0.21,
                        "weighted_score": 0.168,
                        "diagnostics": [
                            {"key": "top_threat_no_answer", "value": 0},
                            {"key": "top_threat_single_answer", "value": 1},
                        ],
                    }
                ],
            },
            "ranking_diagnostics": {
                "key_covered_threats": ["Dialga"],
                "remaining_threats": ["Zygarde"],
                "no_answer_threats": [],
                "single_answer_threats": ["Zygarde"],
                "shared_weaknesses": [
                    {"type": "dark", "members": ["Mewtwo", "Gengar (Mega)"]}
                ],
                "role_assumptions": [
                    "Leads use PvPoke leads rankings when available.",
                    "Back pairs use unordered PvPoke switches, closers, attackers, chargers, and consistency blends when available.",
                ],
                "lineup_dependency": {
                    "dependent": True,
                    "reason": "Only one viable ordered lineup is available.",
                    "best_lineup_score": 621.5,
                    "top_lineup_mean_score": 540.0,
                    "viable_lineup_count": 1,
                },
            },
        },
        "coverage": [
            {"shield": 0, "wins": 1, "draws": 0, "losses": 1, "weighted_wins": 0.5},
        ],
        "recommended_lineups": [
            {
                "lead": {"label": "Mewtwo", "types": ["psychic"]},
                "back_pair": [
                    {"label": "Gengar (Mega)", "types": ["ghost", "poison"]},
                    {"label": "Dialga", "types": ["dragon", "steel"]},
                ],
                "team_shape": "ABC",
                "lineup_score": 621.5,
                "score_summary": {
                    "mean_score": 621.5,
                    "dominating_matchups": 4,
                    "overwhelming_matchups": 1,
                    "resource_mean_score": 621.5,
                    "role_fit_score": 0.8,
                    "synergy_score": 0.7,
                },
                "score_breakdown": {
                    "final_score": 621.5,
                    "components": [
                        {
                            "name": "resource_path",
                            "raw_value": 621.5,
                            "weight": 0.9,
                            "weighted_score": 559.35,
                        },
                        {
                            "name": "role_fit",
                            "raw_value": 800.0,
                            "weight": 0.03,
                            "weighted_score": 24.0,
                        },
                        {
                            "name": "synergy",
                            "raw_value": 700.0,
                            "weight": 0.07,
                            "weighted_score": 49.0,
                        },
                    ],
                },
                "ranking_diagnostics": {
                    "role_assumptions": [
                        "Lead uses PvPoke leads ranking; backs use unordered switch/closer support rankings."
                    ],
                    "shared_weaknesses": [
                        {"type": "dark", "members": ["Mewtwo", "Gengar (Mega)"]}
                    ],
                },
                "resource_paths": [
                    {
                        "name": "balanced",
                        "lead_shield": 1,
                        "back_shield": 1,
                        "mean_best_score": 630.0,
                        "dominating_matchups": 2,
                        "overwhelming_matchups": 0,
                    },
                    {
                        "name": "shield_spend",
                        "lead_shield": 2,
                        "back_shield": 0,
                        "mean_best_score": 610.0,
                        "dominating_matchups": 1,
                        "overwhelming_matchups": 1,
                    },
                    {
                        "name": "shield_save",
                        "lead_shield": 0,
                        "back_shield": 2,
                        "mean_best_score": 624.5,
                        "dominating_matchups": 1,
                        "overwhelming_matchups": 0,
                    },
                ],
                "battle_frontier_points_used": 8,
            }
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


def test_json_exporter_includes_structured_lineups_and_bench_warnings() -> None:
    rendered = JsonExporter().export(build_result())

    assert rendered is not None
    payload = json.loads(rendered)
    assert payload["recommended_lineups"][0]["team_shape"] == "ABC"
    assert payload["recommended_team"]["score_breakdown"]["components"][0]["name"] == "threat_coverage"
    assert payload["recommended_team"]["ranking_diagnostics"]["single_answer_threats"] == ["Zygarde"]
    assert payload["recommended_lineups"][0]["score_breakdown"]["components"][1]["name"] == "role_fit"
    assert payload["recommended_lineups"][0]["resource_paths"][1]["name"] == "shield_spend"
    warning = payload["recommended_team"]["bench_utility"][1]["warnings"][0]
    assert warning == {
        "category": "battle_frontier",
        "code": "expensive_bench",
        "severity": "warning",
        "message": "Expensive Pokemon appears in few viable lineups.",
    }


def test_text_exporter_renders_battle_frontier_legality_metrics() -> None:
    rendered = TextExporter().export(build_result())

    assert rendered is not None
    assert "Battle Frontier legality" in rendered
    assert "points used: 8/11" in rendered
    assert "5-point members: 1/1" in rendered
    assert "Mega members: 1/1" in rendered


def test_text_exporter_renders_lineup_aware_sections() -> None:
    rendered = TextExporter().export(build_result())

    assert rendered is not None
    assert "Recommended Bring-6 Roster" in rendered
    assert "Recommended Lineups" in rendered
    assert "Warnings" in rendered
    assert "#1: Lead Mewtwo | Back Gengar (Mega), Dialga | shape ABC | score 621.50" in rendered
    assert "lineup dominating: 4" in rendered
    assert "lineup overwhelming: 1" in rendered
    assert "lineup dominating: 4 where score > 600" not in rendered
    assert "lineup overwhelming: 1 where score < 400" not in rendered
    assert "resources: balanced mean 630.00 / dom 2 overwhelm 0" in rendered
    assert "| spend mean 610.00 / dom 1 overwhelm 1" in rendered
    assert "expensive_bench [warning]: Expensive Pokemon appears in few viable lineups." in rendered
    assert "Resource / Shield Safety" not in rendered
    assert "\nCoverage\n" not in rendered
    assert "\nSafe Cores\n" not in rendered
    assert "Bench Utility" not in rendered
    assert "full-roster dominate count" in rendered
    assert "ranking-aware score: 0.740" in rendered
    assert "key covered threats: Dialga" in rendered
    assert "remaining threats: Zygarde" in rendered
    assert "shared weaknesses: dark (Mewtwo, Gengar (Mega))" in rendered
    assert "role assumptions: Leads use PvPoke leads rankings when available." in rendered
    assert "lineup dependency [warning]: Only one viable ordered lineup is available." in rendered
    assert "components: resource_path 559.35, role_fit 24.00, synergy 49.00" in rendered
    assert "lineup notes: shared weaknesses dark (Mewtwo, Gengar (Mega))" in rendered
    assert "legacy full-roster dominate count" not in rendered
    assert "where score > 650" not in rendered
    assert "where score < 350" not in rendered


def test_text_exporter_keeps_potential_threats_visible() -> None:
    rendered = TextExporter().export(build_result())

    assert rendered is not None
    assert "Potential Threats" in rendered
    assert "Zygarde | single-coverage: 1 | no-coverage: 0" in rendered


def test_text_exporter_omits_bench_utility_when_no_warnings() -> None:
    result = deepcopy(build_result())
    for entry in result["recommended_team"]["bench_utility"]:  # type: ignore[index]
        entry["warnings"] = []

    rendered = TextExporter().export(result)

    assert rendered is not None
    assert "Bench Utility" not in rendered
    assert "Warnings" not in rendered


def test_markdown_exporter_renders_battle_frontier_legality_metrics() -> None:
    rendered = MarkdownExporter().export(build_result())

    assert rendered is not None
    assert "## Battle Frontier Legality" in rendered
    assert "- Points used: `8/11`" in rendered
    assert "- 5-point members: `1/1`" in rendered
    assert "- Mega members: `1/1`" in rendered


def test_markdown_exporter_renders_lineup_aware_sections() -> None:
    rendered = MarkdownExporter().export(build_result())

    assert rendered is not None
    assert "## Recommended Bring-6 Roster" in rendered
    assert "## Recommended Lineups" in rendered
    assert "## Warnings" in rendered
    assert "balanced mean 630.00 / dom 2 overwhelm 0" in rendered
    assert "| spend mean 610.00 / dom 1 overwhelm 1" in rendered
    assert (
        "Lineup dominating uses resource-path matchup `score > 600`; "
        "lineup overwhelming uses resource-path matchup `score < 400`."
    ) in rendered
    assert (
        "| Gengar (Mega) | battle_frontier | expensive_bench | warning | "
        "Expensive Pokemon appears in few viable lineups. |"
    ) in rendered
    assert "## Resource / Shield Safety" not in rendered
    assert "## Coverage" not in rendered
    assert "## Safe Cores" not in rendered
    assert "## Bench Utility" not in rendered
    assert "Full-roster dominate count" in rendered
    assert "Ranking-aware score: `0.740`" in rendered
    assert "Key covered threats: Dialga" in rendered
    assert "Remaining threats: Zygarde" in rendered
    assert "Shared weaknesses: dark (Mewtwo, Gengar (Mega))" in rendered
    assert "Role assumptions: Leads use PvPoke leads rankings when available." in rendered
    assert "Lineup dependency: Only one viable ordered lineup is available." in rendered
    assert "resource_path `559.35`; role_fit `24.00`; synergy `49.00`" in rendered
    assert "shared weaknesses dark (Mewtwo, Gengar (Mega))" in rendered
    assert "Legacy full-roster dominate count" not in rendered
    assert "score > 650" not in rendered
    assert "score < 350" not in rendered


def test_markdown_exporter_keeps_potential_threats_visible() -> None:
    rendered = MarkdownExporter().export(build_result())

    assert rendered is not None
    assert "## Potential Threats" in rendered
    assert "| Zygarde | 1 | 0 | 0-shield: only Mewtwo (601) |" in rendered


def test_markdown_exporter_omits_bench_utility_when_no_warnings() -> None:
    result = deepcopy(build_result())
    for entry in result["recommended_team"]["bench_utility"]:  # type: ignore[index]
        entry["warnings"] = []

    rendered = MarkdownExporter().export(result)

    assert rendered is not None
    assert "## Bench Utility" not in rendered
    assert "## Warnings" not in rendered


def test_existing_exporters_accept_results_with_battle_frontier_metrics(tmp_path) -> None:
    result = build_result()

    assert '"battle_frontier_points_used": 8' in JsonExporter().export(result)
    CsvExporter().export(result, output_path=str(tmp_path / "result.csv"))


def test_csv_exporter_writes_lineup_and_bench_utility_rows(tmp_path) -> None:
    output_path = tmp_path / "result.csv"

    CsvExporter().export(build_result(), output_path=str(output_path))

    with output_path.open(encoding="utf-8", newline="") as handle:
        rows = list(reader(handle))

    assert rows[0] == ["section", "key", "value"]
    expected_rows = [
        ["recommended_team", "battle_frontier_points_used", "8/11"],
        ["recommended_team", "battle_frontier_five_point_members", "1/1"],
        ["recommended_team", "battle_frontier_mega_members", "1/1"],
        ["recommended_team", "battle_frontier_free_low_point_usage_rate", "0.6667"],
        ["recommended_team", "battle_frontier_high_point_usage_rate", "0.1754"],
        [
            "recommended_lineup",
            "#1",
            "lead=Mewtwo;backs=Gengar (Mega), Dialga;shape=ABC;score=621.50;"
            "mean=621.50;dominating=4;overwhelming=1;points=8",
        ],
        [
            "recommended_lineup_resource_path",
            "#1 balanced",
            "lead_shield=1;back_shield=1;mean_best_score=630.00;"
            "dominating=2;overwhelming=0",
        ],
        [
            "recommended_lineup_resource_path",
            "#1 shield_spend",
            "lead_shield=2;back_shield=0;mean_best_score=610.00;"
            "dominating=1;overwhelming=1",
        ],
        [
            "recommended_lineup_resource_path",
            "#1 shield_save",
            "lead_shield=0;back_shield=2;mean_best_score=624.50;"
            "dominating=1;overwhelming=0",
        ],
        [
            "bench_utility",
            "Mewtwo",
            "tier=core;lineups_used=12;lead_lineups_used=5;back_lineups_used=7;"
            "viable_lineup_rate=0.8000;all_lineup_rate=0.2000;best_lineup_score=640.00",
        ],
        [
            "bench_utility",
            "Gengar (Mega)",
            "tier=low_utility;lineups_used=1;lead_lineups_used=0;back_lineups_used=1;"
            "viable_lineup_rate=0.0500;all_lineup_rate=0.0167;best_lineup_score=525.00",
        ],
        [
            "bench_utility_warning",
            "Gengar (Mega)",
            "category=battle_frontier;code=expensive_bench;severity=warning;"
            "message=Expensive Pokemon appears in few viable lineups.",
        ],
    ]
    section_rows = [
        row
        for row in rows
        if row[0]
        in {
            "recommended_lineup",
            "recommended_lineup_resource_path",
            "bench_utility",
            "bench_utility_warning",
        }
        or row[1].startswith("battle_frontier_")
    ]
    assert section_rows == expected_rows


def test_csv_exporter_sanitizes_bench_utility_key_cells(tmp_path) -> None:
    result = build_result()
    result["recommended_team"]["bench_utility"][0]["member"]["label"] = "=Formula"  # type: ignore[index]
    output_path = tmp_path / "result.csv"

    CsvExporter().export(result, output_path=str(output_path))

    with output_path.open(encoding="utf-8", newline="") as handle:
        rows = list(reader(handle))

    assert any(row[:2] == ["bench_utility", "'=Formula"] for row in rows)


def test_excel_exporter_omits_battle_frontier_lineup_column_when_absent(tmp_path) -> None:
    result = build_result()
    result["recommended_lineups"][0].pop("battle_frontier_points_used")  # type: ignore[index]
    output_path = tmp_path / "result.xlsx"

    ExcelExporter().export(result, output_path=str(output_path))

    with ZipFile(output_path) as workbook:
        lineups_sheet = workbook.read("xl/worksheets/sheet6.xml").decode("utf-8")

    assert "Team Shape" in lineups_sheet
    assert "Battle Frontier Points Used" not in lineups_sheet


def test_excel_exporter_writes_lineup_and_bench_utility_sheets(tmp_path) -> None:
    output_path = tmp_path / "result.xlsx"

    ExcelExporter().export(build_result(), output_path=str(output_path))

    with ZipFile(output_path) as workbook:
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
        lineups_sheet = workbook.read("xl/worksheets/sheet6.xml").decode("utf-8")
        resources_sheet = workbook.read("xl/worksheets/sheet7.xml").decode("utf-8")
        bench_sheet = workbook.read("xl/worksheets/sheet8.xml").decode("utf-8")
        warnings_sheet = workbook.read("xl/worksheets/sheet9.xml").decode("utf-8")

    assert "Lineups" in workbook_xml
    assert "Lineup Resources" in workbook_xml
    assert "Bench Utility" in workbook_xml
    assert "Bench Warnings" in workbook_xml
    assert "Team Shape" in lineups_sheet
    assert "ABC" in lineups_sheet
    assert "Battle Frontier Points Used" in lineups_sheet
    assert "shield_spend" in resources_sheet
    assert "Viable Lineup Rate" in bench_sheet
    assert "expensive_bench" in warnings_sheet


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
