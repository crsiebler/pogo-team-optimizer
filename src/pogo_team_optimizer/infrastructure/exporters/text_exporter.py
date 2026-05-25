from __future__ import annotations

from typing import Any

from pogo_team_optimizer.domain.interfaces import AnalysisExporter


class TextExporter(AnalysisExporter):
    def export(self, result: dict[str, Any], output_path: str | None = None) -> str | None:
        lines: list[str] = []

        if "meta" in result:
            lines.append(f"Meta: {result['meta']}")
            lines.append("")

        lines.append("Recommended Bring-6 Roster")
        for member in result["recommended_team"]["members"]:
            type_text = "/".join(member["types"]) if member["types"] else "unknown"
            lines.append(f"- {member['label']} [{type_text}]")

        lines.append("")
        lines.append("Team Analysis")
        metrics = result["recommended_team"]["metrics"]
        lines.append(
            f"- bulk score: {metrics['bulk_score']:.2f} "
            f"(team avg def*hp/atk; pool min/mean/max "
            f"{metrics['bulk_pool_min']:.2f}/{metrics['bulk_pool_mean']:.2f}/{metrics['bulk_pool_max']:.2f})"
        )
        lines.append(
            f"- safety score: {metrics['safety_score']:.2f} "
            f"(PvPoke switch score avg; pool min/mean/max "
            f"{metrics['safety_pool_min']:.2f}/{metrics['safety_pool_mean']:.2f}/{metrics['safety_pool_max']:.2f})"
        )
        lines.append(
            f"- safety target: {metrics['safety_priority']} priority | avg >= "
            f"{metrics['safety_floor_target']:.2f} | members >= {metrics['safe_member_floor']:.2f}: "
            f"{metrics['safe_member_target']}"
        )
        lines.append(
            f"- consistency score: {metrics['consistency_score']:.2f} "
            "(internal matchup stability metric; not PvPoke bait-dependency consistency) "
            f"= mean {metrics['mean_best_score']:.2f} + dominate bonus - overwhelming penalty"
        )
        lines.append(
            f"- redundancy (2+ winners): {metrics['redundant_coverage_2plus']}/"
            f"{metrics['total_pairs']} ({metrics['redundant_coverage_2plus'] / metrics['total_pairs'] * 100:.1f}%)"
        )
        lines.append(
            f"- redundancy (3+ winners): {metrics['redundant_coverage_3plus']}/"
            f"{metrics['total_pairs']} ({metrics['redundant_coverage_3plus'] / metrics['total_pairs'] * 100:.1f}%)"
        )
        lines.append(
            f"- single-coverage pairs: {metrics['single_cover_pairs']}/{metrics['total_pairs']} "
            f"({metrics['single_cover_rate'] * 100:.1f}%)"
        )
        lines.append(
            f"- no-coverage pairs: {metrics['no_cover_pairs']}/{metrics['total_pairs']} "
            f"({metrics['no_cover_rate'] * 100:.1f}%)"
        )
        lines.append(
            f"- legacy full-roster dominate count: {metrics['dominate_count']}/"
            f"{metrics['total_pairs']} ({metrics['dominate_rate'] * 100:.1f}%)"
        )
        lines.append(
            f"- legacy full-roster overwhelming count: {metrics['overwhelming_count']}/"
            f"{metrics['total_pairs']} ({metrics['overwhelming_rate'] * 100:.1f}%)"
        )
        if "battle_frontier_points_used" in metrics:
            lines.append("")
            lines.append("Battle Frontier legality")
            lines.append(
                f"- points used: {metrics['battle_frontier_points_used']}/"
                f"{metrics['battle_frontier_max_points']}"
            )
            lines.append(
                f"- 5-point members: {metrics['battle_frontier_five_point_members']}/"
                f"{metrics['battle_frontier_max_five_point_members']}"
            )
            lines.append(
                f"- Mega members: {metrics['battle_frontier_mega_members']}/"
                f"{metrics['battle_frontier_max_mega_members']}"
            )

        self._append_recommended_lineups(lines, result)
        self._append_bench_utility(lines, result)

        lines.append("")
        lines.append("Coverage")
        for item in result["coverage"]:
            lines.append(
                f"- {item['shield']}-shield: W {item['wins']} | D {item['draws']} | "
                f"L {item['losses']} | weighted wins {item['weighted_wins']:.3f}"
            )

        lines.append("")
        lines.append("Safe Cores")
        for idx, core in enumerate(result["safe_cores"], start=1):
            if "recommended_order" in core:
                roles = {item["role"]: item["label"] for item in core["recommended_order"]}
                lines.append(
                    f"- #{idx} {core['strategy']}: Lead {roles['lead']} | "
                    f"Switch {roles['switch']} | Closer {roles['closer']}"
                )
            else:
                names = ", ".join(member["label"] for member in core["members"])
                lines.append(f"- #{idx}: {names}")

        lines.append("")
        lines.append("Potential Threats")
        for threat in result["threats"]:
            if threat.get("no_cover_count", 0) == 0 and threat.get("single_cover_count", 0) == 0:
                scores = "/".join(str(score) for score in threat["shield_best_scores"])
                lines.append(
                    f"- {threat['opponent_label']} | no single-cover scenarios | "
                    f"closest scores {scores}"
                )
                continue

            lines.append(
                f"- {threat['opponent_label']} | single-coverage: "
                f"{threat.get('single_cover_count', 0)} | no-coverage: "
                f"{threat.get('no_cover_count', 0)}"
            )
            for fragile in threat.get("fragile_shields", []):
                shield_label = f"{fragile['shield']}-shield"
                if fragile["winner_count"] == 1:
                    lines.append(
                        f"  - {shield_label}: only answer {fragile['only_answer']} "
                        f"({fragile['only_answer_score']})"
                    )
                else:
                    lines.append(
                        f"  - {shield_label}: no cover; best loser "
                        f"{fragile['best_loser']} ({fragile['best_loser_score']})"
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
        lines.append("Recommended Lineups")
        lines.append("- lineup dominating uses score > 600")
        lines.append("- lineup overwhelming uses score < 400")
        for idx, lineup in enumerate(lineups, start=1):
            back_pair = ", ".join(member["label"] for member in lineup["back_pair"])
            summary = lineup["score_summary"]
            points_text = ""
            if "battle_frontier_points_used" in lineup:
                points_text = f" | points {lineup['battle_frontier_points_used']}"
            lines.append(
                f"- #{idx}: Lead {lineup['lead']['label']} | Back {back_pair} | "
                f"shape {lineup.get('team_shape', 'unclassified')} | "
                f"score {lineup['lineup_score']:.2f}{points_text}"
            )
            lines.append(
                f"  - lineup dominating: {summary['dominating_matchups']} where score > 600"
            )
            lines.append(
                f"  - lineup overwhelming: {summary['overwhelming_matchups']} where score < 400"
            )

        lines.append("")
        lines.append("Resource / Shield Safety")
        for idx, lineup in enumerate(lineups, start=1):
            lines.append(f"- Lineup #{idx}")
            for path in lineup["resource_paths"]:
                lines.append(
                    f"  - {path['name']}: lead {path['lead_shield']}-shield | "
                    f"backs {path['back_shield']}-shield | mean {path['mean_best_score']:.2f} | "
                    f"dominating {path['dominating_matchups']} | "
                    f"overwhelming {path['overwhelming_matchups']}"
                )

    def _append_bench_utility(self, lines: list[str], result: dict[str, Any]) -> None:
        utility = result["recommended_team"].get("bench_utility", [])
        if not utility:
            return

        lines.append("")
        lines.append("Bench Utility")
        warnings: list[tuple[str, dict[str, Any]]] = []
        for entry in utility:
            member_label = entry["member"]["label"]
            lines.append(
                f"- {member_label}: {entry['tier']} | used {entry['lineups_used']} lineups | "
                f"lead {entry['lead_lineups_used']} | back {entry['back_lineups_used']} | "
                f"viable {entry['viable_lineup_rate'] * 100:.1f}% | "
                f"all {entry['all_lineup_rate'] * 100:.1f}% | "
                f"best {entry['best_lineup_score']:.2f}"
            )
            for warning in entry.get("warnings", []):
                warnings.append((member_label, warning))

        if warnings:
            lines.append("")
            lines.append("Warnings")
            for member_label, warning in warnings:
                lines.append(
                    f"- {member_label}: {warning['code']} [{warning['severity']}]: "
                    f"{warning['message']}"
                )
