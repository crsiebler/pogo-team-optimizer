from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MetaConfig:
    name: str
    matrix_files: tuple[str, ...]


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

    return MetaConfig(name=meta_name, matrix_files=tuple(matrix_files))


def validate_matrix_files(matrix_files: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for path in matrix_files:
        if not Path(path).exists():
            missing.append(path)
    return missing
