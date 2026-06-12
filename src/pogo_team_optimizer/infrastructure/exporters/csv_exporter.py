from __future__ import annotations

import csv
from typing import Any

from pogo_team_optimizer.domain.interfaces import AnalysisExporter


class CsvExporter(AnalysisExporter):
    def export(self, result: dict[str, Any], output_path: str | None = None) -> str | None:
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
                if "battle_frontier_points_used" in metrics:
                    writer.writerow(
                        [
                            "recommended_team",
                            "battle_frontier_points_used",
                            f"{metrics['battle_frontier_points_used']}/"
                            f"{metrics['battle_frontier_max_points']}",
                        ]
                    )
                if "battle_frontier_five_point_members" in metrics:
                    writer.writerow(
                        [
                            "recommended_team",
                            "battle_frontier_five_point_members",
                            f"{metrics['battle_frontier_five_point_members']}/"
                            f"{metrics['battle_frontier_max_five_point_members']}",
                        ]
                    )
                if "battle_frontier_mega_members" in metrics:
                    writer.writerow(
                        [
                            "recommended_team",
                            "battle_frontier_mega_members",
                            f"{metrics['battle_frontier_mega_members']}/"
                            f"{metrics['battle_frontier_max_mega_members']}",
                        ]
                    )
                if "battle_frontier_free_low_point_usage_rate" in metrics:
                    writer.writerow(
                        [
                            "recommended_team",
                            "battle_frontier_free_low_point_usage_rate",
                            self._format_float(
                                metrics["battle_frontier_free_low_point_usage_rate"], 4
                            ),
                        ]
                    )
                if "battle_frontier_high_point_usage_rate" in metrics:
                    writer.writerow(
                        [
                            "recommended_team",
                            "battle_frontier_high_point_usage_rate",
                            self._format_float(metrics["battle_frontier_high_point_usage_rate"], 4),
                        ]
                    )

            for index, lineup in enumerate(result.get("recommended_lineups", []), start=1):
                writer.writerow(["recommended_lineup", f"#{index}", self._lineup_value(lineup)])
                for resource_path in lineup.get("resource_paths", []):
                    writer.writerow(
                        [
                            "recommended_lineup_resource_path",
                            f"#{index} {resource_path['name']}",
                            self._resource_path_value(resource_path),
                        ]
                    )

            for item in result["recommended_team"].get("bench_utility", []):
                member_label = self._sanitize_cell(item["member"]["label"])
                writer.writerow(["bench_utility", member_label, self._bench_utility_value(item)])
                for warning in item.get("warnings", []):
                    writer.writerow(
                        [
                            "bench_utility_warning",
                            member_label,
                            self._bench_warning_value(warning),
                        ]
                    )

            for item in result["coverage"]:
                writer.writerow(
                    [
                        "coverage",
                        f"{item['shield']}-shield",
                        f"{item['wins']}/{item['draws']}/{item['losses']}",
                    ]
                )

            for index, core in enumerate(result["safe_cores"], start=1):
                if "recommended_order" in core:
                    roles = {item["role"]: item["label"] for item in core["recommended_order"]}
                    writer.writerow(
                        [
                            "safe_core",
                            f"#{index} {core['strategy']}",
                            f"lead={roles['lead']};switch={roles['switch']};closer={roles['closer']}",
                        ]
                    )
                else:
                    writer.writerow(
                        [
                            "safe_core",
                            f"#{index}",
                            ", ".join(member["label"] for member in core["members"]),
                        ]
                    )

            for threat in result["threats"]:
                details: list[str] = []
                for fragile in threat.get("fragile_shields", []):
                    if fragile["winner_count"] == 1:
                        details.append(f"{fragile['shield']}-shield only {fragile['only_answer']}")
                    else:
                        details.append(f"{fragile['shield']}-shield no cover")
                writer.writerow(
                    [
                        "threat",
                        threat["opponent_label"],
                        f"single={threat.get('single_cover_count', 0)};"
                        f"none={threat.get('no_cover_count', 0)};"
                        f"details={' | '.join(details) if details else 'n/a'}",
                    ]
                )

        return None

    def _lineup_value(self, lineup: dict[str, Any]) -> str:
        score_summary = lineup.get("score_summary", {})
        back_pair = lineup.get("back_pair", [])
        value_parts = [
            f"lead={lineup['lead']['label']}",
            f"backs={', '.join(member['label'] for member in back_pair)}",
            f"shape={lineup.get('team_shape', '')}",
            f"score={self._format_float(lineup.get('lineup_score', 0.0), 2)}",
            f"mean={self._format_float(score_summary.get('mean_score', 0.0), 2)}",
            f"dominating={score_summary.get('dominating_matchups', 0)}",
            f"overwhelming={score_summary.get('overwhelming_matchups', 0)}",
        ]
        if "battle_frontier_points_used" in lineup:
            value_parts.append(f"points={lineup['battle_frontier_points_used']}")
        return ";".join(value_parts)

    def _resource_path_value(self, resource_path: dict[str, Any]) -> str:
        return ";".join(
            [
                f"lead_shield={resource_path['lead_shield']}",
                f"back_shield={resource_path['back_shield']}",
                f"mean_best_score={self._format_float(resource_path.get('mean_best_score', 0.0), 2)}",
                f"dominating={resource_path.get('dominating_matchups', 0)}",
                f"overwhelming={resource_path.get('overwhelming_matchups', 0)}",
            ]
        )

    def _bench_utility_value(self, item: dict[str, Any]) -> str:
        return ";".join(
            [
                f"tier={item['tier']}",
                f"lineups_used={item['lineups_used']}",
                f"lead_lineups_used={item['lead_lineups_used']}",
                f"back_lineups_used={item['back_lineups_used']}",
                f"viable_lineup_rate={self._format_float(item['viable_lineup_rate'], 4)}",
                f"all_lineup_rate={self._format_float(item['all_lineup_rate'], 4)}",
                f"best_lineup_score={self._format_float(item['best_lineup_score'], 2)}",
            ]
        )

    def _bench_warning_value(self, warning: dict[str, Any]) -> str:
        return ";".join(
            [
                f"category={warning['category']}",
                f"code={warning['code']}",
                f"severity={warning['severity']}",
                f"message={warning['message']}",
            ]
        )

    def _format_float(self, value: Any, digits: int) -> str:
        return f"{float(value):.{digits}f}"

    def _sanitize_cell(self, value: Any) -> str:
        rendered = str(value)
        if rendered.startswith(("=", "+", "-", "@", "\t", "\r")):
            return f"'{rendered}"
        return rendered
