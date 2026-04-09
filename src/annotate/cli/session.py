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
    """REPL session state: which game is open and which segment is currently selected.

    ``game_id`` is None when no game is open. ``current_turning_point_ply``
    tracks the turning-point ply of the segment that commands like ``view``,
    ``label``, and ``annotate`` operate on by default.
    """

    game_id: str | None = None
    current_turning_point_ply: int | None = None

    @property
    def open(self) -> bool:
        """Return True when a game is currently open for editing."""
        return self.game_id is not None


state = Session()
_repo: JSONFileAnnotationRepository | None = None
_service: AnnotationService | None = None


def get_repo() -> JSONFileAnnotationRepository:
    """Return the shared repository, initialising it on the first call."""
    global _repo
    if _repo is None:
        _repo = JSONFileAnnotationRepository(get_store_dir())
    return _repo


def get_service() -> AnnotationService:
    """Return the shared AnnotationService, initialising it on the first call."""
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
    """Write ``msg`` to stdout."""
    builtins.print(msg)


def err(msg: str) -> None:
    """Write an error message to stderr, prefixed with ``Error:``."""
    builtins.print(f"Error: {msg}", file=sys.stderr)


def prompt(prompt_text: str, default: str | None = None) -> str:
    """Prompt the user for input, re-prompting until a non-empty value is entered.

    When ``default`` is provided, an empty response returns the default and
    the default is shown in brackets in the prompt. When ``default`` is None
    the prompt loops until the user enters at least one non-whitespace character.
    """
    if default is not None:
        text = input(f"{prompt_text} [{default}]: ").strip()
        return text if text else default
    while True:
        text = input(f"{prompt_text}: ").strip()
        if text:
            return text
        print("This field is required.")


def parse_move_side(tokens: list[str], usage: str) -> int | None:
    """Parse a compact move token such as ``14w`` or ``5b`` into a ply number.

    The token format is ``<move_number><w|b>`` where ``w`` is white and ``b``
    is black. Prints a usage error via ``err`` and returns None if the token
    list is empty or the token is malformed.
    """
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
    """Return the current ``game_id``, or print an error and return None if no game is open."""
    if not state.open:
        err("No game is open.")
        return None
    return state.game_id


def current_segments():
    """Return segment summaries for the open game, or None if no game is open."""
    game_id = require_open_session()
    if game_id is None:
        return None
    return get_service().list_segments(game_id=game_id)


def current_segment_summary():
    """Return the SegmentSummary for the currently selected segment.

    Falls back to the first segment when the tracked turning-point ply is
    no longer valid (e.g. after a split or merge). Returns None if no game
    is open.
    """
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
    """Open ``game_id``, update the session state, and print a confirmation.

    Prints an error and leaves the session unchanged if the game is not found.
    """
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
    """Close the current session, prompting the user to save if there are unsaved changes.

    Returns True when the game was successfully closed, False when the user
    chose to cancel or no game is open.
    """
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
