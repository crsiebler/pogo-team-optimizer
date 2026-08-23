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
        self._append_full_team_diagnostics(lines, metrics)
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
            f"- full-roster dominate count: {metrics['dominate_count']}/"
            f"{metrics['total_pairs']} ({metrics['dominate_rate'] * 100:.1f}%)"
        )
        lines.append(
            f"- full-roster overwhelming count: {metrics['overwhelming_count']}/"
            f"{metrics['total_pairs']} ({metrics['overwhelming_rate'] * 100:.1f}%)"
        )
        self._append_ranking_diagnostics(lines, result)
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
        lines.append("Potential Threats")
        self._append_major_threat_groups(lines, result)
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

    def _append_full_team_diagnostics(
        self,
        lines: list[str],
        metrics: dict[str, Any],
    ) -> None:
        grade_fields = (
            ("Coverage Grade", "coverage_grade"),
            ("Bulk Grade", "bulk_grade"),
            ("Safety Grade", "safety_grade"),
            ("Consistency Grade", "consistency_grade"),
        )
        for label, key in grade_fields:
            if key in metrics:
                lines.append(f"- {label}: {metrics[key]}")
        if "threat_score" in metrics:
            lines.append(f"- Threat Score: {metrics['threat_score']:.2f}")

    def _append_major_threat_groups(self, lines: list[str], result: dict[str, Any]) -> None:
        diagnostics = result["recommended_team"].get("ranking_diagnostics", {})
        top_meta_threats = diagnostics.get("major_top_meta_threats", [])
        broad_meta_threats = diagnostics.get("major_broad_meta_threats", [])
        if top_meta_threats:
            lines.append("Major Top-Meta Threats:")
            for threat in top_meta_threats:
                lines.append(f"- {threat}")
        if broad_meta_threats:
            lines.append("Major Broad-Meta Threats:")
            for threat in broad_meta_threats:
                lines.append(f"- {threat}")

    def _append_recommended_lineups(self, lines: list[str], result: dict[str, Any]) -> None:
        lineups = result.get("recommended_lineups", [])
        if not lineups:
            return

        lines.append("")
        lines.append("Recommended Lineups")
        lines.append("- lineup dominating uses resource-path matchup score > 600")
        lines.append("- lineup overwhelming uses resource-path matchup score < 400")
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
            lines.append(f"  - lineup dominating: {summary['dominating_matchups']}")
            lines.append(f"  - lineup overwhelming: {summary['overwhelming_matchups']}")
            resource_summary = " | ".join(
                f"{self._resource_path_label(path['name'])} mean {path['mean_best_score']:.2f} / "
                f"dom {path['dominating_matchups']} overwhelm {path['overwhelming_matchups']}"
                for path in lineup["resource_paths"]
            )
            lines.append(f"  - resources: {resource_summary}")
            component_summary = self._score_component_summary(lineup.get("score_breakdown", {}))
            if component_summary:
                lines.append(f"  - components: {component_summary}")
            lineup_notes = self._lineup_notes(lineup)
            if lineup_notes:
                lines.append(f"  - lineup notes: {lineup_notes}")

    def _append_ranking_diagnostics(self, lines: list[str], result: dict[str, Any]) -> None:
        team = result["recommended_team"]
        score_breakdown = team.get("score_breakdown")
        diagnostics = team.get("ranking_diagnostics")
        if not score_breakdown and not diagnostics:
            return

        if score_breakdown:
            lines.append(f"- ranking-aware score: {score_breakdown['final_score']:.3f}")
        if not diagnostics:
            return

        if diagnostics.get("key_covered_threats"):
            lines.append(
                "- key covered threats: " + ", ".join(diagnostics["key_covered_threats"][:5])
            )
        if diagnostics.get("remaining_threats"):
            lines.append("- remaining threats: " + ", ".join(diagnostics["remaining_threats"][:5]))
        if diagnostics.get("shared_weaknesses"):
            lines.append(
                "- shared weaknesses: "
                + self._format_shared_weaknesses(diagnostics["shared_weaknesses"][:3])
            )
        if diagnostics.get("role_assumptions"):
            lines.append("- role assumptions: " + diagnostics["role_assumptions"][0])
        dependency = diagnostics.get("lineup_dependency", {})
        if dependency.get("dependent"):
            lines.append(f"- lineup dependency [warning]: {dependency['reason']}")

    def _score_component_summary(self, score_breakdown: dict[str, Any]) -> str:
        components = score_breakdown.get("components", [])
        return ", ".join(
            f"{component['name']} {component['weighted_score']:.2f}" for component in components
        )

    def _lineup_notes(self, lineup: dict[str, Any]) -> str:
        diagnostics = lineup.get("ranking_diagnostics", {})
        notes = []
        if diagnostics.get("shared_weaknesses"):
            notes.append(
                "shared weaknesses "
                + self._format_shared_weaknesses(diagnostics["shared_weaknesses"][:3])
            )
        if diagnostics.get("role_assumptions"):
            notes.append(diagnostics["role_assumptions"][0])
        return "; ".join(notes)

    def _format_shared_weaknesses(self, weaknesses: list[dict[str, Any]]) -> str:
        return ", ".join(
            f"{weakness['type']} ({', '.join(weakness['members'])})" for weakness in weaknesses
        )

    def _resource_path_label(self, name: str) -> str:
        return {
            "shield_spend": "spend",
            "shield_save": "save",
        }.get(name, name)

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
            lines.append("Warnings")
            for member_label, warning in warnings:
                lines.append(
                    f"- {member_label}: {warning['code']} [{warning['severity']}]: "
                    f"{warning['message']}"
                )
