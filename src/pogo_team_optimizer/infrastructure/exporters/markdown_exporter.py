from __future__ import annotations

from typing import Any

from pogo_team_optimizer.domain.interfaces import AnalysisExporter


class MarkdownExporter(AnalysisExporter):
    def export(self, result: dict[str, Any], output_path: str | None = None) -> str | None:
        lines: list[str] = []
        lines.append("# Battle Frontier Team Analysis")
        lines.append("")

        if "meta" in result:
            lines.append(f"**Meta:** `{result['meta']}`")
            lines.append("")

        lines.append("## Recommended Bring-6 Roster")
        lines.append("| Pokemon | Types |")
        lines.append("|---|---|")
        for member in result["recommended_team"]["members"]:
            lines.append(
                f"| {self._escape(member['label'])} | "
                f"{self._escape('/'.join(member['types']) or 'unknown')} |"
            )
        metrics = result["recommended_team"]["metrics"]

        lines.append("")
        lines.append("## Team Analysis")
        lines.append(
            "- Bulk score: "
            f"`{metrics['bulk_score']:.2f}` "
            "(team avg `def*hp/atk`; pool min/mean/max "
            f"`{metrics['bulk_pool_min']:.2f}/{metrics['bulk_pool_mean']:.2f}/{metrics['bulk_pool_max']:.2f}`)"
        )
        lines.append(
            "- Safety score: "
            f"`{metrics['safety_score']:.2f}` "
            "(PvPoke switch score avg; pool min/mean/max "
            f"`{metrics['safety_pool_min']:.2f}/{metrics['safety_pool_mean']:.2f}/{metrics['safety_pool_max']:.2f}`)"
        )
        lines.append(
            "- Safety target: "
            f"`{metrics['safety_priority']}` priority, avg >= `{metrics['safety_floor_target']:.2f}`; "
            f"members >= `{metrics['safe_member_floor']:.2f}`: `{metrics['safe_member_target']}`"
        )
        lines.append(
            "- Consistency score: "
            f"`{metrics['consistency_score']:.2f}` "
            "(internal matchup stability metric, not PvPoke bait dependency; "
            f"mean `{metrics['mean_best_score']:.2f}` + dominate bonus - overwhelming penalty)"
        )
        lines.append(
            "- Redundancy (2+ winners): "
            f"`{metrics['redundant_coverage_2plus']}/{metrics['total_pairs']}` "
            f"(`{metrics['redundant_coverage_2plus'] / metrics['total_pairs'] * 100:.1f}%`)"
        )
        lines.append(
            "- Redundancy (3+ winners): "
            f"`{metrics['redundant_coverage_3plus']}/{metrics['total_pairs']}` "
            f"(`{metrics['redundant_coverage_3plus'] / metrics['total_pairs'] * 100:.1f}%`)"
        )
        lines.append(
            "- Single-coverage pairs: "
            f"`{metrics['single_cover_pairs']}/{metrics['total_pairs']}` "
            f"(`{metrics['single_cover_rate'] * 100:.1f}%`)"
        )
        lines.append(
            "- No-coverage pairs: "
            f"`{metrics['no_cover_pairs']}/{metrics['total_pairs']}` "
            f"(`{metrics['no_cover_rate'] * 100:.1f}%`)"
        )
        lines.append(
            "- Legacy full-roster dominate count: "
            f"`{metrics['dominate_count']}/{metrics['total_pairs']}` "
            f"(`{metrics['dominate_rate'] * 100:.1f}%`)"
        )
        lines.append(
            "- Legacy full-roster overwhelming count: "
            f"`{metrics['overwhelming_count']}/{metrics['total_pairs']}` "
            f"(`{metrics['overwhelming_rate'] * 100:.1f}%`)"
        )
        if "battle_frontier_points_used" in metrics:
            lines.append("")
            lines.append("## Battle Frontier Legality")
            lines.append(
                "- Points used: "
                f"`{metrics['battle_frontier_points_used']}/{metrics['battle_frontier_max_points']}`"
            )
            lines.append(
                "- 5-point members: "
                f"`{metrics['battle_frontier_five_point_members']}/"
                f"{metrics['battle_frontier_max_five_point_members']}`"
            )
            lines.append(
                "- Mega members: "
                f"`{metrics['battle_frontier_mega_members']}/{metrics['battle_frontier_max_mega_members']}`"
            )

        self._append_recommended_lineups(lines, result)
        self._append_bench_utility(lines, result)

        lines.append("")
        lines.append("## Potential Threats")
        lines.append("| Opponent | Single-Coverage | No-Coverage | Details |")
        lines.append("|---|---:|---:|---|")
        for threat in result["threats"]:
            details: list[str] = []
            for fragile in threat.get("fragile_shields", []):
                shield_label = f"{fragile['shield']}-shield"
                if fragile["winner_count"] == 1:
                    details.append(
                        f"{shield_label}: only {fragile['only_answer']} ({fragile['only_answer_score']})"
                    )
                else:
                    details.append(
                        f"{shield_label}: no cover, best loser {fragile['best_loser']} "
                        f"({fragile['best_loser_score']})"
                    )
            if not details:
                details.append(
                    "closest " + "/".join(str(score) for score in threat["shield_best_scores"])
                )
            lines.append(
                f"| {threat['opponent_label']} | {threat.get('single_cover_count', 0)} | "
                f"{threat.get('no_cover_count', 0)} | {'; '.join(details)} |"
            )

        rendered = "\n".join(lines)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(rendered)
            return None
        return rendered

    def _append_recommended_lineups(self, lines: list[str], result: dict[str, Any]) -> None:
        lineups = result.get("recommended_lineups", [])
        if not lineups:
            return

        lines.append("")
        lines.append("## Recommended Lineups")
        lines.append("Lineup dominating uses `score > 600`; lineup overwhelming uses `score < 400`.")
        lines.append("")
        lines.append(
            "| # | Lead | Back Pair | Shape | Score | Dominating | Overwhelming | "
            "BF Points | Resources |"
        )
        lines.append("|---:|---|---|---|---:|---:|---:|---:|---|")
        for idx, lineup in enumerate(lineups, start=1):
            back_pair = ", ".join(member["label"] for member in lineup["back_pair"])
            summary = lineup["score_summary"]
            points = lineup.get("battle_frontier_points_used", "")
            resource_summary = "; ".join(
                f"{path['name']} lead/back {path['lead_shield']}/{path['back_shield']} "
                f"mean {path['mean_best_score']:.2f} dom {path['dominating_matchups']} "
                f"overwhelm {path['overwhelming_matchups']}"
                for path in lineup["resource_paths"]
            )
            lines.append(
                f"| {idx} | {self._escape(lineup['lead']['label'])} | "
                f"{self._escape(back_pair)} | {self._escape(lineup.get('team_shape', 'unclassified'))} | "
                f"{lineup['lineup_score']:.2f} | {summary['dominating_matchups']} | "
                f"{summary['overwhelming_matchups']} | {points} | "
                f"{self._escape(resource_summary)} |"
            )

    def _append_bench_utility(self, lines: list[str], result: dict[str, Any]) -> None:
        utility = result["recommended_team"].get("bench_utility", [])
        if not utility:
            return

        warnings: list[tuple[str, dict[str, Any]]] = []
        for entry in utility:
            member_label = entry["member"]["label"]
            for warning in entry.get("warnings", []):
                warnings.append((member_label, warning))

        if warnings:
            lines.append("")
            lines.append("## Warnings")
            lines.append("| Pokemon | Category | Code | Severity | Message |")
            lines.append("|---|---|---|---|---|")
            for member_label, warning in warnings:
                lines.append(
                    f"| {self._escape(member_label)} | {self._escape(warning['category'])} | "
                    f"{self._escape(warning['code'])} | {self._escape(warning['severity'])} | "
                    f"{self._escape(warning['message'])} |"
                )

    def _escape(self, value: object) -> str:
        return str(value).replace("|", "\\|")
