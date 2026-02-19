import pytest

from pogo_team_optimizer.infrastructure.exporters.factory import ExporterFactory


def test_exporter_factory_supports_markdown() -> None:
    exporter = ExporterFactory.create("markdown")
    assert exporter.__class__.__name__ == "MarkdownExporter"


def test_exporter_factory_rejects_unknown_format() -> None:
    with pytest.raises(ValueError):
        ExporterFactory.create("xml")


def test_exporter_factory_requires_paths_for_pvpoke() -> None:
    with pytest.raises(ValueError):
        ExporterFactory.create("pvpoke")
