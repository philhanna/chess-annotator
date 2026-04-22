from pathlib import Path

from annotate.adapters.pgn_repository import parse_pgn_collection
from annotate.service import AnnotateSession


def test_new_session_starts_idle(tmp_path: Path) -> None:
    session = AnnotateSession(frontend_root=tmp_path)

    snapshot = session.snapshot()

    assert snapshot.app_name == "chess-annotate"
    assert snapshot.frontend_root == str(tmp_path)
    assert snapshot.status == "idle"
    assert snapshot.source_name is None
    assert snapshot.selected_game_index is None
    assert snapshot.selected_ply is None
    assert snapshot.unsaved_changes is False


def test_parse_pgn_collection_handles_multiple_games() -> None:
    pgn_text = Path("tests/testdata/annotate-multi.pgn").read_text()

    games = parse_pgn_collection(pgn_text)

    assert len(games) == 2
    assert games[0].summary.white == "Tom Smith"
    assert games[1].summary.white == "Nakamura"


def test_open_pgn_builds_document_view(tmp_path: Path) -> None:
    session = AnnotateSession(frontend_root=tmp_path)
    pgn_text = Path("tests/testdata/game3.pgn").read_text()

    view = session.open_pgn("game3.pgn", pgn_text)

    assert view["session"]["status"] == "document-loaded"
    assert view["session"]["source_name"] == "game3.pgn"
    assert view["selected_game"]["white"] == "Nakamura"
    assert view["selected_ply"] == 1
    assert view["editor"]["comment"] == ""
    assert any(row["diagram"] for row in view["move_rows"])
    assert view["board_svg"].startswith("<svg")


def test_select_ply_updates_editor_state(tmp_path: Path) -> None:
    session = AnnotateSession(frontend_root=tmp_path)
    pgn_text = Path("tests/testdata/game3.pgn").read_text()
    session.open_pgn("game3.pgn", pgn_text)

    view = session.select_ply(10)

    assert view["selected_ply"] == 10
    assert view["editor"]["diagram"] is True
    assert "I played the standard Scandinavian opening" in view["editor"]["comment"]


def test_navigate_moves_between_plies(tmp_path: Path) -> None:
    session = AnnotateSession(frontend_root=tmp_path)
    pgn_text = Path("tests/testdata/game1.pgn").read_text()
    session.open_pgn("game1.pgn", pgn_text)

    session.navigate("next")
    view = session.navigate("end")

    assert view["selected_ply"] == 58

    view = session.navigate("start")
    assert view["selected_ply"] == 1


def test_select_game_switches_active_game(tmp_path: Path) -> None:
    session = AnnotateSession(frontend_root=tmp_path)
    pgn_text = Path("tests/testdata/annotate-multi.pgn").read_text()
    session.open_pgn("annotate-multi.pgn", pgn_text)

    view = session.select_game(1)

    assert view["selected_game"]["index"] == 1
    assert view["selected_game"]["white"] == "Nakamura"
    assert view["selected_ply"] == 1
