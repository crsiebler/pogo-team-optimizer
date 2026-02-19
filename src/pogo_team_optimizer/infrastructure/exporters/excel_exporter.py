from __future__ import annotations

from pogo_team_optimizer.domain.interfaces import AnalysisExporter


class ExcelExporter(AnalysisExporter):
    def export(self, result: dict, output_path: str | None = None) -> str | None:
        raise NotImplementedError(
            "Excel export is not implemented yet. Add openpyxl and implement ExcelExporter."
        )
