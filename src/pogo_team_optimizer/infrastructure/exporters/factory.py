from __future__ import annotations

from pogo_team_optimizer.domain.interfaces import AnalysisExporter
from pogo_team_optimizer.infrastructure.exporters.csv_exporter import CsvExporter
from pogo_team_optimizer.infrastructure.exporters.excel_exporter import ExcelExporter
from pogo_team_optimizer.infrastructure.exporters.json_exporter import JsonExporter
from pogo_team_optimizer.infrastructure.exporters.markdown_exporter import MarkdownExporter
from pogo_team_optimizer.infrastructure.exporters.pvpoke_exporter import PvpokeExporter
from pogo_team_optimizer.infrastructure.exporters.text_exporter import TextExporter


class ExporterFactory:
    @staticmethod
    def create(
        output_format: str,
        *,
        pokemon_path: str | None = None,
        moves_path: str | None = None,
    ) -> AnalysisExporter:
        mapping: dict[str, type[AnalysisExporter]] = {
            "text": TextExporter,
            "markdown": MarkdownExporter,
            "json": JsonExporter,
            "csv": CsvExporter,
            "excel": ExcelExporter,
        }
        if output_format == "pvpoke":
            if pokemon_path is None or moves_path is None:
                raise ValueError("pokemon_path and moves_path are required for pvpoke export")
            return PvpokeExporter(pokemon_path=pokemon_path, moves_path=moves_path)
        try:
            return mapping[output_format]()
        except KeyError as exc:
            raise ValueError(f"Unsupported format: {output_format}") from exc
