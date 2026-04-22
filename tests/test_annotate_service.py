from pathlib import Path

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

