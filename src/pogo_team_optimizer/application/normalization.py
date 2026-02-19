from __future__ import annotations

import re


def parse_species(label: str) -> str:
    stripped = re.sub(r"\s+\d+/\d+/\d+$", "", label.strip())
    move_match = re.search(r"\s+[A-Za-z]+\+[^ ]+$", stripped)
    if move_match:
        stripped = stripped[: move_match.start()]
    return stripped.strip()


def parse_base_species(species: str) -> str:
    return species.replace(" (Shadow)", "")


def is_shadow(species: str) -> bool:
    return "(Shadow)" in species
