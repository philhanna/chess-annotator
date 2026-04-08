from pathlib import Path

import pytest

from annotate.adapters.pgn_file_game_repository import PGNFileGameRepository
from annotate.adapters.python_chess_pgn_parser import PythonChessPGNParser
from annotate.domain.annotation import Annotation
from annotate.domain.segment import SegmentContent
from annotate.use_cases.services import (
    AnnotationService,
    GameNotFoundError,
    MissingDependencyError,
    OverwriteRequiredError,
    SegmentNotFoundError,
    SessionNotOpenError,
    UseCaseError,
)

_PGN = (
    "[Event \"Club Championship\"]\n"
    "[White \"Alice\"]\n"
    "[Black \"Bob\"]\n"
    "[Date \"2024.05.01\"]\n"
    "[Result \"1-0\"]\n"
    "\n"
    "1. e4 {comment} e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 "
    "5. O-O Be7 6. Re1 b5 7. Bb3 d6 *\n"
)

_PGN_2 = (
    "[Event \"Casual\"]\n"
    "[White \"Carol\"]\n"
    "[Black \"Dan\"]\n"
    "[Date \"2024.05.02\"]\n"
    "[Result \"0-1\"]\n"
    "\n"
    "1. d4 d5 2. c4 e6 *\n"
)


class FakeDocumentRenderer:
    def __init__(self) -> None:
        self.calls = []

    def render(self, annotation, output_path, diagram_size, page_size, store_dir) -> None:
        self.calls.append(
            {
                "annotation": annotation,
                "output_path": output_path,
                "diagram_size": diagram_size,
                "page_size": page_size,
                "store_dir": store_dir,
            }
        )
        Path(output_path).write_text("pdf")


class FakeLichessUploader:
    def __init__(self) -> None:
        self.uploads = []

    def upload(self, pgn_text: str) -> str:
        self.uploads.append(pgn_text)
        return "https://lichess.org/abc123"


class FakeDiagramRenderer:
    def __init__(self) -> None:
        self.calls = []

    def render(self, pgn, end_ply, orientation, size, cache_dir):
        self.calls.append((pgn, end_ply, orientation, size, cache_dir))
        cache_dir.mkdir(parents=True, exist_ok=True)
        output = cache_dir / f"{end_ply}.svg"
        output.write_text("<svg/>")
        return output


def make_service(tmp_path, **overrides):
    repo = overrides.pop("repository", PGNFileGameRepository(tmp_path))
    parser = overrides.pop("pgn_parser", PythonChessPGNParser())
    return AnnotationService(
        repository=repo,
        pgn_parser=parser,
        store_dir=tmp_path,
        **overrides,
    )


def save_game(repo, game_id="game-1"):
    annotation = Annotation(
        game_id=game_id,
        title="Alice - Bob 2024.05.01",
        author="Tester",
        date="2024-05-01",
        pgn=_PGN.replace("{comment} ", ""),
        player_side="white",
        diagram_orientation="white",
        turning_points=[1, 5],
        segment_contents={
            1: SegmentContent(label="Opening", annotation="Develop"),
            5: SegmentContent(label="Plan", annotation="Pressure e5"),
        },
    )
    repo.save(annotation)
    return annotation


def test_import_game_creates_main_and_working_state(tmp_path):
    service = make_service(tmp_path)

    state = service.import_game(
        game_id="game-1",
        pgn_text=_PGN,
        player_side="white",
        author="Tester",
    )

    assert state.game_id == "game-1"
    assert state.session_open is True
    assert state.has_unsaved_changes is False
    assert len(state.segments) == 1
    saved = service.repository.load("game-1")
    assert "{comment}" not in saved.pgn
    assert service.repository.exists_working_copy("game-1") is True


def test_import_game_requires_overwrite_flag(tmp_path):
    service = make_service(tmp_path)
    service.import_game(game_id="game-1", pgn_text=_PGN, player_side="white")

    with pytest.raises(OverwriteRequiredError):
        service.import_game(game_id="game-1", pgn_text=_PGN, player_side="white")


def test_import_game_can_select_later_game_from_multi_pgn(tmp_path):
    service = make_service(tmp_path)

    service.import_game(
        game_id="game-2",
        pgn_text=f"{_PGN}\n{_PGN_2}",
        player_side="black",
        game_index=1,
    )

    annotation = service.repository.load("game-2")
    assert "Carol" in annotation.title
    assert "Dan" in annotation.title


def test_list_games_reports_metadata_and_in_progress(tmp_path):
    service = make_service(tmp_path)
    service.import_game(game_id="game-1", pgn_text=_PGN, player_side="white")

    summaries = service.list_games()

    assert len(summaries) == 1
    assert summaries[0].white == "Alice"
    assert summaries[0].black == "Bob"
    assert summaries[0].event == "Club Championship"
    assert summaries[0].result == "1-0"
    assert summaries[0].in_progress is True


def test_open_game_resumes_existing_working_copy(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    repo.save_working_copy(annotation)
    service = make_service(tmp_path, repository=repo)

    state = service.open_game("game-1")

    assert state.session_open is True
    assert state.resumed is True


def test_save_game_as_uses_working_copy_when_available(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    annotation.segment_contents[5].annotation = "Working update"
    repo.save_working_copy(annotation)
    service = make_service(tmp_path, repository=repo)

    service.save_game_as(source_game_id="game-1", new_game_id="copy-1")

    copied = repo.load("copy-1")
    assert copied.segment_contents[5].annotation == "Working update"
    assert repo.exists_working_copy("copy-1") is False


def test_delete_game_removes_game_directory(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    save_game(repo)
    service = make_service(tmp_path, repository=repo)

    service.delete_game("game-1")

    assert repo.exists("game-1") is False


def test_segment_edit_use_cases_require_open_session(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    save_game(repo)
    service = make_service(tmp_path, repository=repo)

    with pytest.raises(SessionNotOpenError):
        service.list_segments(game_id="game-1")


def test_add_and_remove_turning_point_update_working_copy(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    repo.save_working_copy(annotation)
    service = make_service(tmp_path, repository=repo)

    segments = service.add_turning_point(game_id="game-1", ply=9, label="Attack")
    assert [segment.turning_point_ply for segment in segments] == [1, 5, 9]

    segments = service.remove_turning_point(game_id="game-1", ply=9, force=True)
    assert [segment.turning_point_ply for segment in segments] == [1, 5]


def test_setters_and_toggle_return_updated_segment(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    repo.save_working_copy(annotation)
    service = make_service(tmp_path, repository=repo)

    detail = service.set_segment_label(game_id="game-1", turning_point_ply=5, label="Kingside Plan")
    assert detail.label == "Kingside Plan"

    detail = service.set_segment_annotation(
        game_id="game-1",
        turning_point_ply=5,
        annotation_text="Double rooks on the e-file",
    )
    assert "Double rooks" in detail.annotation

    toggled = service.toggle_segment_diagram(game_id="game-1", turning_point_ply=5)
    assert toggled.show_diagram is False


def test_blank_label_and_annotation_are_rejected(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    repo.save_working_copy(annotation)
    service = make_service(tmp_path, repository=repo)

    with pytest.raises(UseCaseError):
        service.set_segment_label(game_id="game-1", turning_point_ply=1, label="  ")
    with pytest.raises(UseCaseError):
        service.set_segment_annotation(game_id="game-1", turning_point_ply=1, annotation_text=" ")


def test_save_and_close_session_flows(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    repo.save_working_copy(annotation)
    service = make_service(tmp_path, repository=repo)

    service.set_segment_annotation(
        game_id="game-1",
        turning_point_ply=5,
        annotation_text="Updated in session",
    )
    state = service.save_session("game-1")
    assert state.has_unsaved_changes is False
    assert repo.load("game-1").segment_contents[5].annotation == "Updated in session"

    close = service.close_game("game-1")
    assert close.closed is True
    assert repo.exists_working_copy("game-1") is False


def test_close_game_requests_confirmation_for_unsaved_changes(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    repo.save_working_copy(annotation)
    service = make_service(tmp_path, repository=repo)

    service.set_segment_annotation(
        game_id="game-1",
        turning_point_ply=5,
        annotation_text="Unsaved",
    )

    result = service.close_game("game-1", save_changes=None)
    assert result.requires_confirmation is True
    assert result.closed is False

    result = service.close_game("game-1", save_changes=False)
    assert result.closed is True
    assert result.discarded is True


def test_render_pdf_uses_working_copy_when_present(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    annotation.segment_contents[5].annotation = "Working text"
    repo.save(annotation)
    repo.save_working_copy(annotation)
    renderer = FakeDocumentRenderer()
    service = make_service(tmp_path, repository=repo, document_renderer=renderer)

    output_path = service.render_pdf(game_id="game-1", diagram_size=200, page_size="letter")

    assert output_path == tmp_path / "game-1" / "output.pdf"
    assert renderer.calls[0]["annotation"].segment_contents[5].annotation == "Working text"
    assert output_path.exists()


def test_render_pdf_requires_renderer(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    save_game(repo)
    service = make_service(tmp_path, repository=repo)

    with pytest.raises(MissingDependencyError):
        service.render_pdf(game_id="game-1")


def test_upload_to_lichess_uses_current_state(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    repo.save_working_copy(annotation)
    uploader = FakeLichessUploader()
    service = make_service(tmp_path, repository=repo, lichess_uploader=uploader)

    url = service.upload_to_lichess(game_id="game-1")

    assert url == "https://lichess.org/abc123"
    assert uploader.uploads


def test_view_segment_returns_move_list_and_diagram_preview(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    repo.save_working_copy(annotation)
    diagram_renderer = FakeDiagramRenderer()
    service = make_service(tmp_path, repository=repo, diagram_renderer=diagram_renderer)

    detail = service.view_segment(game_id="game-1", turning_point_ply=5)

    assert detail.label == "Plan"
    assert "3. Bb5" in detail.move_list
    assert detail.diagram_path is not None
    assert diagram_renderer.calls


def test_view_segment_rejects_missing_segment(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = save_game(repo)
    repo.save_working_copy(annotation)
    service = make_service(tmp_path, repository=repo)

    with pytest.raises(SegmentNotFoundError):
        service.view_segment(game_id="game-1", turning_point_ply=99)


def test_game_not_found_is_reported(tmp_path):
    service = make_service(tmp_path)

    with pytest.raises(GameNotFoundError):
        service.open_game("missing")
