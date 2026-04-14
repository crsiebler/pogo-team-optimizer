from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MetaConfig:
    name: str
    matrix_files: tuple[str, ...]
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

    switch_rankings_path = meta_value.get("switch_rankings_path")
    if switch_rankings_path is not None and not isinstance(switch_rankings_path, str):
        raise ValueError(f"Meta '{meta_name}' must define string 'switch_rankings_path'")

    required_files = meta_value.get("required_files", [])
    if not isinstance(required_files, list) or not all(isinstance(v, str) for v in required_files):
        raise ValueError(f"Meta '{meta_name}' must define string list 'required_files'")

    return MetaConfig(
        name=meta_name,
        matrix_files=tuple(matrix_files),
        switch_rankings_path=switch_rankings_path,
        required_files=tuple(required_files),
    )


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
