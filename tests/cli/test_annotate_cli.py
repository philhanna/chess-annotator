from pathlib import Path
from types import SimpleNamespace

import pytest

from annotate.cli import annotate
from annotate.use_cases import OverwriteRequiredError


class FakeRepo:
    def stale_working_copies(self):
        return []


class FakeService:
    def __init__(self) -> None:
        self.import_calls = 0
        self.open_calls = []
        self.list_segment_calls = []
        self.view_calls = []
        self.save_calls = []
        self.close_calls = []

    def import_game(self, **kwargs):
        self.import_calls += 1
        if self.import_calls == 1:
            raise OverwriteRequiredError("exists")
        return SimpleNamespace(
            game_id=kwargs["game_id"],
            title="Imported Game",
            session_open=True,
            has_unsaved_changes=False,
            segments=[SimpleNamespace(turning_point_ply=1)],
        )

    def open_game(self, game_id):
        self.open_calls.append(game_id)
        return SimpleNamespace(
            game_id=game_id,
            title="Opened Game",
            session_open=True,
            has_unsaved_changes=False,
            resumed=False,
            segments=[SimpleNamespace(turning_point_ply=1, move_range="1. e4 to 10...Nc6", label="Opening")],
        )

    def list_segments(self, *, game_id):
        self.list_segment_calls.append(game_id)
        return [
            SimpleNamespace(
                turning_point_ply=1,
                move_range="1. e4 to 10...Nc6",
                label="Opening",
                has_annotation=True,
                show_diagram=True,
            )
        ]

    def view_segment(self, *, game_id, turning_point_ply):
        self.view_calls.append((game_id, turning_point_ply))
        return SimpleNamespace(
            turning_point_ply=turning_point_ply,
            move_range="1. e4 to 10...Nc6",
            label="Opening",
            move_list="1. e4 e5 2. Nf3 Nc6",
            show_diagram=True,
            annotation="Plan the opening.",
            diagram_path=None,
        )

    def save_session(self, game_id):
        self.save_calls.append(game_id)
        return SimpleNamespace(has_unsaved_changes=False)

    def close_game(self, game_id, save_changes=None):
        self.close_calls.append((game_id, save_changes))
        return SimpleNamespace(closed=True, requires_confirmation=False)


@pytest.fixture(autouse=True)
def reset_cli_state():
    annotate._session.game_id = None
    annotate._session.current_turning_point_ply = None
    annotate._repo = None
    annotate._service = None
    yield
    annotate._session.game_id = None
    annotate._session.current_turning_point_ply = None
    annotate._repo = None
    annotate._service = None


def test_repl_open_list_view_save_and_quit(monkeypatch, capsys):
    fake_service = FakeService()
    monkeypatch.setattr(annotate, "get_service", lambda: fake_service)
    monkeypatch.setattr(annotate, "get_repo", lambda: FakeRepo())
    inputs = iter(["open game-1", "list", "view 1", "save", "quit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    with pytest.raises(SystemExit):
        annotate.main()

    out = capsys.readouterr().out
    assert "Opened: Opened Game" in out
    assert "1. e4 to 10...Nc6" in out
    assert "Plan the opening." in out
    assert "Saved." in out
    assert fake_service.open_calls == ["game-1", "game-1"]
    assert fake_service.save_calls == ["game-1"]


def test_repl_import_handles_overwrite_prompt(monkeypatch, tmp_path, capsys):
    fake_service = FakeService()
    pgn_path = tmp_path / "game.pgn"
    pgn_path.write_text(
        "[Event \"Test\"]\n[White \"White\"]\n[Black \"Black\"]\n[Date \"2024.01.01\"]\n\n1. e4 e5 *\n"
    )
    monkeypatch.setattr(annotate, "get_service", lambda: fake_service)
    monkeypatch.setattr(annotate, "get_repo", lambda: FakeRepo())
    monkeypatch.setattr(
        annotate,
        "get_config",
        lambda: SimpleNamespace(author="Tester", diagram_size=360, page_size="a4"),
    )
    inputs = iter(
        [
            f"import {pgn_path}",
            "game-1",
            "2024.01.01",
            "white",
            "white",
            "yes",
            "quit",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    with pytest.raises(SystemExit):
        annotate.main()

    out = capsys.readouterr().out
    assert "Imported and opened: Imported Game" in out
    assert fake_service.import_calls == 2
