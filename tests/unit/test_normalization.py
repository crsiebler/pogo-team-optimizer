from pogo_team_optimizer.application.normalization import parse_base_species, parse_species


def test_parse_species_strips_moves_and_ivs() -> None:
    label = "Charizard (Shadow) E+AC/BB 4/13/14"
    assert parse_species(label) == "Charizard (Shadow)"


def test_parse_base_species_strips_shadow() -> None:
    assert parse_base_species("Empoleon (Shadow)") == "Empoleon"
