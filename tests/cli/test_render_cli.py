from pathlib import Path
from types import SimpleNamespace

import pytest

from annotate.cli import render


class FakeService:
    def __init__(self) -> None:
        self.calls = []

    def render_pdf(self, *, game_id, diagram_size, page_size, output_path=None):
        self.calls.append((game_id, diagram_size, page_size, output_path))
        Path(output_path).write_text("pdf")
        return Path(output_path)


class FakeRepo:
    def __init__(self, pgn_text, working_pgn_text=None) -> None:
        self.pgn_text = pgn_text
        self.working_pgn_text = working_pgn_text

    def exists(self, game_id):
        return game_id == "game-1"

    def exists_working_copy(self, game_id):
        return game_id == "game-1" and self.working_pgn_text is not None

    def load(self, game_id):
        return SimpleNamespace(pgn=self.pgn_text)

    def load_working_copy(self, game_id):
        return SimpleNamespace(pgn=self.working_pgn_text)


def test_render_cli_uses_service(monkeypatch, tmp_path, capsys):
    fake_service = FakeService()
    fake_repo = FakeRepo(
        '[Event "Test"]\n\n1. e4 {note} e5 $1 *\n',
    )
    monkeypatch.setattr(render, "build_repository", lambda: fake_repo)
    monkeypatch.setattr(render, "build_service", lambda repository=None: fake_service)
    monkeypatch.setattr(
        render,
        "get_config",
        lambda: SimpleNamespace(diagram_size=320, page_size="a4", store_dir=Path("/tmp/store")),
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["chess-render", "game-1", "--size", "200", "--page", "letter"])

    render.main()

    out = capsys.readouterr().out
    assert fake_service.calls == [("game-1", 200, "letter", tmp_path / "game-1.pdf")]
    assert f"Rendered PDF: {tmp_path / 'game-1.pdf'}" in out
    assert f"Exported PGN: {tmp_path / 'game-1.pgn'}" in out
    assert (tmp_path / "game-1.pgn").read_text() == '[Event "Test"]\n\n1. e4 e5 *'


def test_render_cli_writes_artifacts_to_requested_directory(monkeypatch, tmp_path, capsys):
    fake_service = FakeService()
    output_dir = tmp_path / "artifacts"
    fake_repo = FakeRepo(
        '[Event "Test"]\n\n1. e4 {note} e5 *\n',
        working_pgn_text='[Event "Test"]\n\n1. d4 {work} d5 *\n',
    )
    monkeypatch.setattr(render, "build_repository", lambda: fake_repo)
    monkeypatch.setattr(render, "build_service", lambda repository=None: fake_service)
    monkeypatch.setattr(
        render,
        "get_config",
        lambda: SimpleNamespace(diagram_size=320, page_size="a4", store_dir=Path("/tmp/store")),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["chess-render", "game-1", "--dir", str(output_dir)],
    )

    render.main()

    capsys.readouterr()
    assert fake_service.calls == [("game-1", 320, "a4", output_dir / "game-1.pdf")]
    assert (output_dir / "game-1.pdf").exists()
    assert (output_dir / "game-1.pgn").read_text() == '[Event "Test"]\n\n1. d4 d5 *'


def test_render_cli_reports_errors(monkeypatch, capsys):
    class BoomService:
        def render_pdf(self, **_kwargs):
            raise ValueError("missing annotation")

    monkeypatch.setattr(render, "build_repository", lambda: FakeRepo('[Event "Test"]\n\n1. e4 e5 *\n'))
    monkeypatch.setattr(render, "build_service", lambda repository=None: BoomService())
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
