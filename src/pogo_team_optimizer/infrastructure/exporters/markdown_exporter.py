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

        lines.append("## Recommended Team")
        lines.append("| Pokemon | Types |")
        lines.append("|---|---|")
        for member in result["recommended_team"]["members"]:
            lines.append(f"| {member['label']} | {'/'.join(member['types']) or 'unknown'} |")
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
            "- Dominate: "
            f"`{metrics['dominate_count']}/{metrics['total_pairs']}` "
            f"(`{metrics['dominate_rate'] * 100:.1f}%`, score > 650)"
        )
        lines.append(
            "- Overwhelming: "
            f"`{metrics['overwhelming_count']}/{metrics['total_pairs']}` "
            f"(`{metrics['overwhelming_rate'] * 100:.1f}%`, score < 350)"
        )

        lines.append("")
        lines.append("## Coverage")
        lines.append("| Shield | Wins | Draws | Losses | Weighted Wins |")
        lines.append("|---:|---:|---:|---:|---:|")
        for item in result["coverage"]:
            lines.append(
                f"| {item['shield']} | {item['wins']} | {item['draws']} | "
                f"{item['losses']} | {item['weighted_wins']:.3f} |"
            )

        lines.append("")
        lines.append("## Safe Cores")
        for idx, core in enumerate(result["safe_cores"], start=1):
            names = ", ".join(member["label"] for member in core["members"])
            lines.append(f"- **#{idx}** {names}")

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
