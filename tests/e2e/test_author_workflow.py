from pathlib import Path

from annotate.adapters.markdown_html_pdf_renderer import MarkdownHTMLPDFRenderer
from annotate.adapters.pgn_file_game_repository import PGNFileGameRepository
from annotate.adapters.python_chess_diagram_renderer import PythonChessDiagramRenderer
from annotate.adapters.python_chess_pgn_parser import PythonChessPGNParser
from annotate.use_cases.services import AnnotationService


class FakeLichessUploader:
    def __init__(self) -> None:
        self.uploads: list[str] = []

    def upload(self, pgn_text: str) -> str:
        self.uploads.append(pgn_text)
        return "https://lichess.org/e2e123"


def load_test_pgn() -> str:
    path = Path(__file__).resolve().parents[1] / "testdata" / "game1.pgn"
    return path.read_text()


def build_service(tmp_path, uploader=None) -> AnnotationService:
    return AnnotationService(
        repository=PGNFileGameRepository(tmp_path),
        pgn_parser=PythonChessPGNParser(),
        store_dir=tmp_path,
        document_renderer=MarkdownHTMLPDFRenderer(
            diagram_renderer=PythonChessDiagramRenderer()
        ),
        lichess_uploader=uploader,
        diagram_renderer=PythonChessDiagramRenderer(),
    )


def test_end_to_end_author_workflow(tmp_path):
    uploader = FakeLichessUploader()
    service = build_service(tmp_path, uploader=uploader)

    imported = service.import_game(
        game_id="workflow-game",
        pgn_text=load_test_pgn(),
        player_side="white",
        author="Tester",
        date="2024-05-01",
    )
    assert imported.session_open is True
    assert len(imported.segments) == 1

    segments = service.add_turning_point(
        game_id="workflow-game",
        ply=15,
        label="Plan Shift",
    )
    assert [segment.turning_point_ply for segment in segments] == [1, 15]

    service.set_segment_label(
        game_id="workflow-game",
        turning_point_ply=1,
        label="Opening",
    )
    service.set_segment_annotation(
        game_id="workflow-game",
        turning_point_ply=1,
        annotation_text="Develop pieces and prepare central play.",
    )
    service.set_segment_annotation(
        game_id="workflow-game",
        turning_point_ply=15,
        annotation_text="Shift to kingside pressure and piece activity.",
    )

    listed = service.list_segments(game_id="workflow-game")
    assert [segment.label for segment in listed] == ["Opening", "Plan Shift"]

    detail = service.view_segment(game_id="workflow-game", turning_point_ply=15)
    assert "kingside pressure" in detail.annotation
    assert detail.move_list

    saved = service.save_session("workflow-game")
    assert saved.has_unsaved_changes is False

    pdf_path = service.render_pdf(game_id="workflow-game")
    assert pdf_path.exists()
    assert pdf_path.name == "output.pdf"

    url = service.upload_to_lichess(game_id="workflow-game")
    assert url == "https://lichess.org/e2e123"
    assert uploader.uploads

    close = service.close_game("workflow-game")
    assert close.closed is True

    reopened = service.open_game("workflow-game")
    assert reopened.resumed is False
    assert reopened.session_open is True


def test_crash_resume_from_existing_work_files(tmp_path):
    uploader = FakeLichessUploader()
    first_service = build_service(tmp_path, uploader=uploader)
    first_service.import_game(
        game_id="resume-game",
        pgn_text=load_test_pgn(),
        player_side="white",
    )
    first_service.set_segment_label(
        game_id="resume-game",
        turning_point_ply=1,
        label="Unsaved Opening",
    )
    first_service.set_segment_annotation(
        game_id="resume-game",
        turning_point_ply=1,
        annotation_text="Unsaved notes survive the crash.",
    )

    second_service = build_service(tmp_path, uploader=uploader)
    reopened = second_service.open_game("resume-game")
    assert reopened.resumed is True
    assert reopened.has_unsaved_changes is True

    detail = second_service.view_segment(
        game_id="resume-game",
        turning_point_ply=1,
    )
    assert detail.label == "Unsaved Opening"
    assert "survive the crash" in detail.annotation
