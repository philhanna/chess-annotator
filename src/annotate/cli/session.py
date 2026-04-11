import builtins
import sys
from dataclasses import dataclass

from annotate.adapters.json_file_annotation_repository import JSONFileAnnotationRepository
from annotate.adapters.lichess_api_uploader import LichessAPIUploader
from annotate.adapters.markdown_html_pdf_renderer import MarkdownHTMLPDFRenderer
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
    """Module-level REPL session state: which game is open and which segment is selected.

    ``game_id`` is None when no game is open. ``current_turning_point_ply`` tracks
    the turning-point ply of the segment that commands such as ``view``, ``label``,
    and ``edit`` operate on by default.
    """

    game_id: str | None = None
    current_turning_point_ply: int | None = None

    @property
    def open(self) -> bool:
        """Return True when a game is currently open for editing."""
        return self.game_id is not None


# Module-level singletons — initialised lazily on first use.
state = Session()
_repo: JSONFileAnnotationRepository | None = None
_service: AnnotationService | None = None


def get_repo() -> JSONFileAnnotationRepository:
    """Return the shared repository instance, creating it on the first call."""
    global _repo
    if _repo is None:
        _repo = JSONFileAnnotationRepository(get_store_dir())
    return _repo


def get_service() -> AnnotationService:
    """Return the shared ``AnnotationService`` instance, creating it on the first call.

    Wires all concrete adapters together using the current application config.
    """
    global _service
    if _service is None:
        config = get_config()
        _service = AnnotationService(
            repository=get_repo(),
            pgn_parser=PythonChessPGNParser(),
            store_dir=config.store_dir,
            document_renderer=MarkdownHTMLPDFRenderer(),
            lichess_uploader=LichessAPIUploader(),
        )
    return _service


def print(msg: str = "") -> None:
    """Write ``msg`` to stdout, followed by a newline.

    Shadows the built-in ``print`` within this module to provide a single
    controlled output channel for all REPL messages.
    """
    builtins.print(msg)


def err(msg: str) -> None:
    """Write an error message to stderr, prefixed with ``"Error: "``."""
    builtins.print(f"Error: {msg}", file=sys.stderr)


def prompt(prompt_text: str, default: str | None = None) -> str:
    """Prompt the user for input, re-prompting until a non-empty value is entered.

    When ``default`` is provided, an empty response returns the default value and
    the default is shown in square brackets in the prompt text. When ``default`` is
    None the loop continues until the user types at least one non-whitespace character.
    """
    if default is not None:
        text = input(f"{prompt_text} [{default}]: ").strip()
        # An empty response accepts the default.
        return text if text else default
    while True:
        text = input(f"{prompt_text}: ").strip()
        if text:
            return text
        print("This field is required.")


def parse_move_side(tokens: list[str], usage: str) -> int | None:
    """Parse a compact move token such as ``"14w"`` or ``"5b"`` into a 1-based ply number.

    The expected token format is ``<move_number><w|b>`` where ``w`` means White and
    ``b`` means Black. Prints a usage error via ``err`` and returns None when the
    token list is empty or the token is malformed.

    Args:
        tokens: The remaining command tokens; the first element is parsed.
        usage:  The usage string to display on error.
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
    """Return the current ``game_id`` if a session is open, otherwise print an error and return None."""
    if not state.open:
        err("No game is open.")
        return None
    return state.game_id


def current_segments():
    """Return ``SegmentSummary`` objects for every segment in the open game.

    Returns None (and prints an error) if no game is currently open.
    """
    game_id = require_open_session()
    if game_id is None:
        return None
    return get_service().list_segments(game_id=game_id)


def current_segment_summary():
    """Return the ``SegmentSummary`` for the currently selected segment.

    Falls back to the first segment when the tracked turning-point ply is no longer
    valid — for example, after a split or merge that changed the segment structure.
    Returns None if no game is open.
    """
    segments = current_segments()
    if not segments:
        return None
    # Seed the selection to the first segment when none is tracked yet.
    if state.current_turning_point_ply is None:
        state.current_turning_point_ply = segments[0].turning_point_ply
    # Try to find the previously selected segment.
    for seg in segments:
        if seg.turning_point_ply == state.current_turning_point_ply:
            return seg
    # The previously selected segment no longer exists — reset to segment 1.
    state.current_turning_point_ply = segments[0].turning_point_ply
    return segments[0]


def open_game(game_id: str) -> None:
    """Open ``game_id``, update the session state, and print a confirmation message.

    Prints an error and leaves the session unchanged if the game is not found or
    any other use-case error occurs.
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
    # Default segment selection to the first segment of the opened game.
    state.current_turning_point_ply = (
        game_state.segments[0].turning_point_ply if game_state.segments else None
    )
    print(f"Opened: {game_state.title}{' (resumed)' if game_state.resumed else ''}")


def do_close() -> bool:
    """Close the current session, prompting the user to save if there are unsaved changes.

    Returns True when the game was successfully closed, False when the user chose to
    cancel or when no game is open.
    """
    game_id = require_open_session()
    if game_id is None:
        return False
    try:
        # First call with save_changes=None to detect whether confirmation is needed.
        result = get_service().close_game(game_id, save_changes=None)
    except UseCaseError as exc:
        err(str(exc))
        return False
    if result.requires_confirmation:
        # Ask the user what to do with the unsaved changes.
        answer = input("You have unsaved changes. Save before closing? (yes/no/cancel): ").strip().lower()
        if answer == "cancel":
            print("Close cancelled.")
            return False
        save_changes = answer == "yes"
        result = get_service().close_game(game_id, save_changes=save_changes)
    # Clear session state regardless of whether changes were saved or discarded.
    state.game_id = None
    state.current_turning_point_ply = None
    print("Session closed.")
    return True
