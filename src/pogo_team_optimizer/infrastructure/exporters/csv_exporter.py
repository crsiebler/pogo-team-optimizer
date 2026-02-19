from __future__ import annotations

import csv

from pogo_team_optimizer.domain.interfaces import AnalysisExporter


class CsvExporter(AnalysisExporter):
    def export(self, result: dict, output_path: str | None = None) -> str | None:
        if output_path is None:
            raise ValueError("--output is required for csv format")

        with open(output_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["section", "key", "value"])

            for member in result["recommended_team"]["members"]:
                writer.writerow(["recommended_team", "member", member["label"]])

            metrics = result["recommended_team"].get("metrics", {})
            if metrics:
                writer.writerow(["recommended_team", "bulk_score", f"{metrics['bulk_score']:.2f}"])
                writer.writerow(
                    [
                        "recommended_team",
                        "bulk_pool_min_mean_max",
                        f"{metrics['bulk_pool_min']:.2f}/{metrics['bulk_pool_mean']:.2f}/{metrics['bulk_pool_max']:.2f}",
                    ]
                )
                writer.writerow(
                    [
                        "recommended_team",
                        "consistency",
                        f"score={metrics['consistency_score']:.2f};mean={metrics['mean_best_score']:.2f};"
                        f"dominate={metrics['dominate_count']}/{metrics['total_pairs']};"
                        f"overwhelming={metrics['overwhelming_count']}/{metrics['total_pairs']}",
                    ]
                )
                writer.writerow(
                    [
                        "recommended_team",
                        "redundancy",
                        f"2plus={metrics['redundant_coverage_2plus']}/{metrics['total_pairs']};"
                        f"3plus={metrics['redundant_coverage_3plus']}/{metrics['total_pairs']};"
                        f"single={metrics['single_cover_pairs']}/{metrics['total_pairs']};"
                        f"none={metrics['no_cover_pairs']}/{metrics['total_pairs']}",
                    ]
                )

            for item in result["coverage"]:
                writer.writerow(["coverage", f"{item['shield']}-shield", f"{item['wins']}/{item['draws']}/{item['losses']}"])

            for threat in result["threats"]:
                details: list[str] = []
                for fragile in threat.get("fragile_shields", []):
                    if fragile["winner_count"] == 1:
                        details.append(
                            f"{fragile['shield']}-shield only {fragile['only_answer']}"
                        )
                    else:
                        details.append(f"{fragile['shield']}-shield no cover")
                writer.writerow([
                    "threat",
                    threat["opponent_label"],
                    f"single={threat.get('single_cover_count', 0)};"
                    f"none={threat.get('no_cover_count', 0)};"
                    f"details={' | '.join(details) if details else 'n/a'}",
                ])

        return None
