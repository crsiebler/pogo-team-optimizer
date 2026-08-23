from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from pogo_team_optimizer.domain.interfaces import AnalysisExporter


class ExcelExporter(AnalysisExporter):
    def export(self, result: dict[str, Any], output_path: str | None = None) -> str | None:
        if output_path is None:
            raise ValueError("--output is required for excel format")

        sheets = self._build_sheets(result)
        with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as workbook:
            workbook.writestr("[Content_Types].xml", self._content_types(len(sheets)))
            workbook.writestr("_rels/.rels", self._package_relationships())
            workbook.writestr("xl/workbook.xml", self._workbook_xml([name for name, _ in sheets]))
            workbook.writestr(
                "xl/_rels/workbook.xml.rels", self._workbook_relationships(len(sheets))
            )
            for index, (_, rows) in enumerate(sheets, start=1):
                workbook.writestr(f"xl/worksheets/sheet{index}.xml", self._sheet_xml(rows))

        return None

    def _build_sheets(self, result: dict[str, Any]) -> list[tuple[str, list[list[object]]]]:
        recommended_rows: list[list[object]] = [["Recommended Team"], ["Pokemon", "Types"]]
        for member in result["recommended_team"]["members"]:
            recommended_rows.append([member["label"], "/".join(member["types"]) or "unknown"])

        metric_rows: list[list[object]] = [["Metric", "Value"]]
        metrics = result["recommended_team"].get("metrics", {})
        for key, value in sorted(metrics.items()):
            metric_rows.append([key, value])

        coverage_rows: list[list[object]] = [["Shield", "Wins", "Draws", "Losses", "Weighted Wins"]]
        for item in result["coverage"]:
            coverage_rows.append(
                [item["shield"], item["wins"], item["draws"], item["losses"], item["weighted_wins"]]
            )

        core_rows: list[list[object]] = [["Rank", "Strategy", "Lead", "Switch", "Closer"]]
        for index, core in enumerate(result["safe_cores"], start=1):
            if "recommended_order" in core:
                roles = {item["role"]: item["label"] for item in core["recommended_order"]}
                core_rows.append(
                    [
                        index,
                        core["strategy"],
                        roles["lead"],
                        roles["switch"],
                        roles["closer"],
                    ]
                )
            else:
                core_rows.append(
                    [index, "", ", ".join(member["label"] for member in core["members"]), "", ""]
                )

        threat_rows: list[list[object]] = [
            ["Opponent", "Single Coverage", "No Coverage", "Details"]
        ]
        for threat in result["threats"]:
            details: list[str] = []
            for fragile in threat.get("fragile_shields", []):
                if fragile["winner_count"] == 1:
                    details.append(f"{fragile['shield']}-shield only {fragile['only_answer']}")
                else:
                    details.append(f"{fragile['shield']}-shield no cover")
            threat_rows.append(
                [
                    threat["opponent_label"],
                    threat.get("single_cover_count", 0),
                    threat.get("no_cover_count", 0),
                    " | ".join(details) if details else "n/a",
                ]
            )

        lineup_rows = self._lineup_rows(result.get("recommended_lineups", []))
        lineup_resource_rows = self._lineup_resource_rows(result.get("recommended_lineups", []))
        bench_rows, bench_warning_rows = self._bench_utility_rows(
            result["recommended_team"].get("bench_utility", [])
        )

        return [
            ("Recommended", recommended_rows),
            ("Metrics", metric_rows),
            ("Coverage", coverage_rows),
            ("Safe Cores", core_rows),
            ("Threats", threat_rows),
            ("Lineups", lineup_rows),
            ("Lineup Resources", lineup_resource_rows),
            ("Bench Utility", bench_rows),
            ("Bench Warnings", bench_warning_rows),
        ]

    def _lineup_rows(self, lineups: list[dict[str, Any]]) -> list[list[object]]:
        include_battle_frontier_points = any(
            "battle_frontier_points_used" in lineup for lineup in lineups
        )
        header: list[object] = [
            "Rank",
            "Lead",
            "Back 1",
            "Back 2",
            "Team Shape",
            "Lineup Score",
            "Mean Score",
            "Dominating Matchups",
            "Overwhelming Matchups",
        ]
        if include_battle_frontier_points:
            header.append("Battle Frontier Points Used")
        rows: list[list[object]] = [header]
        for index, lineup in enumerate(lineups, start=1):
            back_pair = lineup.get("back_pair", [])
            score_summary = lineup.get("score_summary", {})
            row: list[object] = [
                index,
                lineup["lead"]["label"],
                back_pair[0]["label"] if len(back_pair) > 0 else "",
                back_pair[1]["label"] if len(back_pair) > 1 else "",
                lineup.get("team_shape", ""),
                lineup.get("lineup_score", ""),
                score_summary.get("mean_score", ""),
                score_summary.get("dominating_matchups", ""),
                score_summary.get("overwhelming_matchups", ""),
            ]
            if include_battle_frontier_points:
                row.append(lineup.get("battle_frontier_points_used", ""))
            rows.append(row)
        return rows

    def _lineup_resource_rows(self, lineups: list[dict[str, Any]]) -> list[list[object]]:
        rows: list[list[object]] = [
            [
                "Lineup Rank",
                "Path",
                "Lead Shield",
                "Back Shield",
                "Mean Best Score",
                "Dominating Matchups",
                "Overwhelming Matchups",
            ]
        ]
        for index, lineup in enumerate(lineups, start=1):
            for resource_path in lineup.get("resource_paths", []):
                rows.append(
                    [
                        index,
                        resource_path["name"],
                        resource_path["lead_shield"],
                        resource_path["back_shield"],
                        resource_path.get("mean_best_score", ""),
                        resource_path.get("dominating_matchups", ""),
                        resource_path.get("overwhelming_matchups", ""),
                    ]
                )
        return rows

    def _bench_utility_rows(
        self, bench_utility: list[dict[str, Any]]
    ) -> tuple[list[list[object]], list[list[object]]]:
        rows: list[list[object]] = [
            [
                "Pokemon",
                "Tier",
                "Lineups Used",
                "Lead Lineups Used",
                "Back Lineups Used",
                "Viable Lineup Rate",
                "All Lineup Rate",
                "Best Lineup Score",
            ]
        ]
        warning_rows: list[list[object]] = [["Pokemon", "Category", "Code", "Severity", "Message"]]
        for item in bench_utility:
            member_label = item["member"]["label"]
            rows.append(
                [
                    member_label,
                    item["tier"],
                    item["lineups_used"],
                    item["lead_lineups_used"],
                    item["back_lineups_used"],
                    item["viable_lineup_rate"],
                    item["all_lineup_rate"],
                    item["best_lineup_score"],
                ]
            )
            for warning in item.get("warnings", []):
                warning_rows.append(
                    [
                        member_label,
                        warning["category"],
                        warning["code"],
                        warning["severity"],
                        warning["message"],
                    ]
                )
        return rows, warning_rows

    def _content_types(self, sheet_count: int) -> str:
        sheet_overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, sheet_count + 1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            f"{sheet_overrides}"
            "</Types>"
        )

    def _package_relationships(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

    def _workbook_xml(self, sheet_names: list[str]) -> str:
        sheets = "".join(
            f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
            for index, name in enumerate(sheet_names, start=1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{sheets}</sheets>"
            "</workbook>"
        )

    def _workbook_relationships(self, sheet_count: int) -> str:
        relationships = "".join(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, sheet_count + 1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{relationships}"
            "</Relationships>"
        )

    def _sheet_xml(self, rows: list[list[object]]) -> str:
        row_xml = "".join(
            f'<row r="{row_index}">{self._row_cells(row, row_index)}</row>'
            for row_index, row in enumerate(rows, start=1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{row_xml}</sheetData>"
            "</worksheet>"
        )

    def _row_cells(self, row: list[object], row_index: int) -> str:
        return "".join(
            self._cell_xml(self._column_name(column_index), row_index, value)
            for column_index, value in enumerate(row, start=1)
        )

    def _cell_xml(self, column_name: str, row_index: int, value: object) -> str:
        cell_reference = f"{column_name}{row_index}"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{cell_reference}"><v>{value}</v></c>'
        return f'<c r="{cell_reference}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'

    def _column_name(self, column_index: int) -> str:
        name = ""
        while column_index > 0:
            column_index, remainder = divmod(column_index - 1, 26)
            name = chr(65 + remainder) + name
        return name
