from __future__ import annotations

import json

from pogo_team_optimizer.domain.interfaces import AnalysisExporter


class JsonExporter(AnalysisExporter):
    def export(self, result: dict, output_path: str | None = None) -> str | None:
        rendered = json.dumps(result, indent=2)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(rendered)
            return None
        return rendered
