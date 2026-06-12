from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pogo_team_optimizer.domain.models import RankingCategory


@dataclass(frozen=True)
class MetaConfig:
    name: str
    matrix_files: tuple[str, ...]
    ranking_paths: Mapping[RankingCategory, str] = field(default_factory=dict)
    full_meta_ranking_paths: Mapping[RankingCategory, str] = field(default_factory=dict)
    switch_rankings_path: str | None = None
    required_files: tuple[str, ...] = ()


def load_meta_config(config_path: str, meta_name: str) -> MetaConfig:
    config_file = Path(config_path)
    with config_file.open(encoding="utf-8") as handle:
        data = json.load(handle)

    metas = data.get("metas")
    if not isinstance(metas, dict):
        raise ValueError("Invalid metas config: missing 'metas' object")

    meta_value = metas.get(meta_name)
    if not isinstance(meta_value, dict):
        available = ", ".join(sorted(metas.keys()))
        raise ValueError(f"Unknown meta '{meta_name}'. Available metas: {available}")

    matrix_files = meta_value.get("matrix_files")
    if not isinstance(matrix_files, list) or not all(isinstance(v, str) for v in matrix_files):
        raise ValueError(f"Meta '{meta_name}' must define string list 'matrix_files'")

    ranking_paths = _parse_ranking_paths(meta_name, meta_value.get("ranking_paths"), "ranking_paths")
    full_meta_ranking_paths = _parse_ranking_paths(
        meta_name,
        meta_value.get("full_meta_ranking_paths"),
        "full_meta_ranking_paths",
    )

    switch_rankings_path = meta_value.get("switch_rankings_path")
    if switch_rankings_path is not None and not isinstance(switch_rankings_path, str):
        raise ValueError(f"Meta '{meta_name}' must define string 'switch_rankings_path'")
    if switch_rankings_path is not None:
        configured_switch_path = ranking_paths.get(RankingCategory.SWITCHES)
        if configured_switch_path is not None and configured_switch_path != switch_rankings_path:
            raise ValueError(
                f"Meta '{meta_name}' has conflicting switch ranking paths between "
                "'switch_rankings_path' and 'ranking_paths.switches'"
            )
        ranking_paths[RankingCategory.SWITCHES] = switch_rankings_path
    switch_rankings_path = ranking_paths.get(RankingCategory.SWITCHES)

    required_files = meta_value.get("required_files", [])
    if not isinstance(required_files, list) or not all(isinstance(v, str) for v in required_files):
        raise ValueError(f"Meta '{meta_name}' must define string list 'required_files'")

    return MetaConfig(
        name=meta_name,
        matrix_files=tuple(matrix_files),
        ranking_paths=ranking_paths,
        full_meta_ranking_paths=full_meta_ranking_paths,
        switch_rankings_path=switch_rankings_path,
        required_files=tuple(required_files),
    )


def _parse_ranking_paths(
    meta_name: str,
    value: object,
    field_name: str,
) -> dict[RankingCategory, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Meta '{meta_name}' must define object '{field_name}'")

    ranking_paths: dict[RankingCategory, str] = {}
    for category_text, path in value.items():
        if not isinstance(category_text, str):
            raise ValueError(f"Meta '{meta_name}' {field_name} keys must be strings")
        try:
            category = RankingCategory(category_text)
        except ValueError as error:
            supported = ", ".join(category.value for category in RankingCategory)
            raise ValueError(
                f"Unsupported ranking category '{category_text}' in meta '{meta_name}' "
                f"{field_name}. Expected one of: {supported}"
            ) from error
        if not isinstance(path, str):
            raise ValueError(
                f"Meta '{meta_name}' {field_name}.{category.value} must be a string path"
            )
        ranking_paths[category] = path
    return ranking_paths


def validate_matrix_files(matrix_files: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for path in matrix_files:
        if not Path(path).exists():
            missing.append(path)
    return missing


def validate_required_files(required_files: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for path in required_files:
        if not Path(path).exists():
            missing.append(path)
    return missing


def validate_ranking_files(*ranking_path_mappings: Mapping[RankingCategory, str]) -> list[str]:
    missing: list[str] = []
    seen: set[str] = set()
    for ranking_paths in ranking_path_mappings:
        for path in ranking_paths.values():
            if path in seen:
                continue
            seen.add(path)
            if not Path(path).exists():
                missing.append(path)
    return missing
