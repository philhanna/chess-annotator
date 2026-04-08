from pathlib import Path
from types import SimpleNamespace

import pytest

from annotate.cli import render


class FakeService:
    def __init__(self) -> None:
        self.calls = []

    def render_pdf(self, *, game_id, diagram_size, page_size):
        self.calls.append((game_id, diagram_size, page_size))
        return Path(f"/tmp/{game_id}/output.pdf")


def test_render_cli_uses_service(monkeypatch, capsys):
    fake_service = FakeService()
    monkeypatch.setattr(render, "build_service", lambda: fake_service)
    monkeypatch.setattr(
        render,
        "get_config",
        lambda: SimpleNamespace(diagram_size=320, page_size="a4", store_dir=Path("/tmp/store")),
    )
    monkeypatch.setattr("sys.argv", ["chess-render", "game-1", "--size", "200", "--page", "letter"])

    render.main()

    out = capsys.readouterr().out
    assert fake_service.calls == [("game-1", 200, "letter")]
    assert "Rendered: /tmp/game-1/output.pdf" in out


def test_render_cli_reports_errors(monkeypatch, capsys):
    class BoomService:
        def render_pdf(self, **_kwargs):
            raise ValueError("missing annotation")

    monkeypatch.setattr(render, "build_service", lambda: BoomService())
    monkeypatch.setattr(
        render,
        "get_config",
        lambda: SimpleNamespace(diagram_size=320, page_size="a4", store_dir=Path("/tmp/store")),
    )
    monkeypatch.setattr("sys.argv", ["chess-render", "game-1"])

    with pytest.raises(SystemExit):
        render.main()

    err = capsys.readouterr().err
    assert "Error: missing annotation" in err
