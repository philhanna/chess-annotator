# annotate.cli.session
import builtins
import sys
from dataclasses import dataclass

from annotate.adapters.json_file_annotation_repository import JSONFileAnnotationRepository
from annotate.adapters.lichess_api_uploader import LichessAPIUploader
from annotate.adapters.markdown_html_pdf_renderer import MarkdownHTMLPDFRenderer
from annotate.adapters.python_chess_diagram_renderer import PythonChessDiagramRenderer
from annotate.adapters.python_chess_pgn_parser import PythonChessPGNParser
from annotate.config import get_config, get_store_dir
from annotate.domain.model import ply_from_move
from annotate.use_cases import (
    AnnotationService,
    GameNotFoundError,
    UseCaseError,
)


@dataclass
class Session:
    game_id: str | None = None
    current_turning_point_ply: int | None = None

    @property
    def open(self) -> bool:
        return self.game_id is not None


state = Session()
_repo: JSONFileAnnotationRepository | None = None
_service: AnnotationService | None = None


def get_repo() -> JSONFileAnnotationRepository:
    global _repo
    if _repo is None:
        _repo = JSONFileAnnotationRepository(get_store_dir())
    return _repo


def get_service() -> AnnotationService:
    global _service
    if _service is None:
        config = get_config()
        _service = AnnotationService(
            repository=get_repo(),
            pgn_parser=PythonChessPGNParser(),
            store_dir=config.store_dir,
            document_renderer=MarkdownHTMLPDFRenderer(),
            lichess_uploader=LichessAPIUploader(),
            diagram_renderer=PythonChessDiagramRenderer(),
        )
    return _service


def print(msg: str = "") -> None:
    builtins.print(msg)


def err(msg: str) -> None:
    builtins.print(f"Error: {msg}", file=sys.stderr)


def prompt(prompt_text: str, default: str | None = None) -> str:
    if default is not None:
        text = input(f"{prompt_text} [{default}]: ").strip()
        return text if text else default
    while True:
        text = input(f"{prompt_text}: ").strip()
        if text:
            return text
        print("This field is required.")


def parse_move_side(tokens: list[str], usage: str) -> int | None:
    if not tokens:
        err(f"Usage: {usage}")
        return None
    token = tokens[0].lower()
    if not token or token[-1] not in ("w", "b"):
        err(f"Usage: {usage}")
        return None
    try:
        move_number = int(token[:-1])
    except ValueError:
        err(f"Usage: {usage}")
        return None
    side = "white" if token[-1] == "w" else "black"
    return ply_from_move(move_number, side)


def require_open_session() -> str | None:
    if not state.open:
        err("No game is open.")
        return None
    return state.game_id


def current_segments():
    game_id = require_open_session()
    if game_id is None:
        return None
    return get_service().list_segments(game_id=game_id)


def current_segment_summary():
    segments = current_segments()
    if not segments:
        return None
    if state.current_turning_point_ply is None:
        state.current_turning_point_ply = segments[0].turning_point_ply
    for seg in segments:
        if seg.turning_point_ply == state.current_turning_point_ply:
            return seg
    state.current_turning_point_ply = segments[0].turning_point_ply
    return segments[0]


def open_game(game_id: str) -> None:
    try:
        game_state = get_service().open_game(game_id)
    except GameNotFoundError as exc:
        err(str(exc))
        return
    except UseCaseError as exc:
        err(str(exc))
        return
    state.game_id = game_state.game_id
    state.current_turning_point_ply = (
        game_state.segments[0].turning_point_ply if game_state.segments else None
    )
    print(f"Opened: {game_state.title}{' (resumed)' if game_state.resumed else ''}")


def do_close() -> bool:
    game_id = require_open_session()
    if game_id is None:
        return False
    try:
        result = get_service().close_game(game_id, save_changes=None)
    except UseCaseError as exc:
        err(str(exc))
        return False
    if result.requires_confirmation:
        answer = input("You have unsaved changes. Save before closing? (yes/no/cancel): ").strip().lower()
        if answer == "cancel":
            print("Close cancelled.")
            return False
        save_changes = answer == "yes"
        result = get_service().close_game(game_id, save_changes=save_changes)
    state.game_id = None
    state.current_turning_point_ply = None
    print("Session closed.")
    return True
