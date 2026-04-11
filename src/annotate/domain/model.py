import io
import re
from dataclasses import dataclass

import chess.pgn

from annotate.domain.annotation import Annotation
from annotate.domain.segment import SegmentContent, SegmentView


@dataclass(frozen=True)
class DiagramToken:
    """A parsed ``[[diagram ...]]`` token found in annotation text.

    ``ply`` is the 1-based ply number derived from the move notation in the
    token. ``orientation`` is ``"white"`` or ``"black"`` (defaults to
    ``"white"`` when omitted from the token). ``raw`` is the original matched
    string and is used by the renderer to locate the token for substitution.
    """

    ply: int
    orientation: str
    raw: str


# Matches [[diagram <move><side> [<orientation>]]] tokens in annotation text.
# Group 1: move number (integer)
# Group 2: side letter ("w" or "b")
# Group 3: optional orientation ("white" or "black")
_DIAGRAM_TOKEN_RE = re.compile(
    r"\[\[diagram\s+(\d+)(w|b)(?:\s+(white|black))?\]\]"
)


def parse_diagram_tokens(text: str) -> list[DiagramToken]:
    """Return all ``[[diagram ...]]`` tokens found in ``text``, in order.

    Each token specifies a ply (via move notation) and an optional board
    orientation. The move notation is converted to a 1-based ply index using
    ``ply_from_move``. Orientation defaults to ``"white"`` when omitted.

    Tokens with invalid move notation (move number zero or negative) are
    silently skipped.
    """
    tokens: list[DiagramToken] = []
    for m in _DIAGRAM_TOKEN_RE.finditer(text):
        move_number = int(m.group(1))
        side = "white" if m.group(2) == "w" else "black"
        orientation = m.group(3) or "white"
        try:
            ply = ply_from_move(move_number, side)
        except ValueError:
            continue
        tokens.append(DiagramToken(ply=ply, orientation=orientation, raw=m.group(0)))
    return tokens


def total_plies(pgn: str) -> int:
    """Return the number of half-moves (plies) in the main line of a PGN game.

    Raises ``ValueError`` if the PGN string cannot be parsed.
    """
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse PGN")
    return sum(1 for _ in game.mainline_moves())


def game_headers(pgn: str) -> dict[str, str]:
    """Return all PGN headers for the first game as a plain ``{key: value}`` dict.

    Raises ``ValueError`` if the PGN string cannot be parsed.
    """
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse PGN")
    # Convert both keys and values to plain strings to strip any chess.pgn wrappers.
    return {str(key): str(value) for key, value in game.headers.items()}


def ply_from_move(move_number: int, side: str) -> int:
    """Convert a move number and side (``"white"`` or ``"black"``) to a 1-based ply index.

    Ply numbering starts at 1 for White's first move:
    * move 1 white → ply 1
    * move 1 black → ply 2
    * move 2 white → ply 3
    * …

    Raises ``ValueError`` if ``side`` is not ``"white"`` or ``"black"``.
    """
    if side not in ("white", "black"):
        raise ValueError(f"side must be 'white' or 'black', got {side!r}")
    # White moves occupy odd plies, black moves occupy even plies.
    side_offset = 1 if side == "white" else 2
    return (move_number - 1) * 2 + side_offset


def move_from_ply(ply: int) -> tuple[int, str]:
    """Convert a 1-based ply index to a ``(move_number, side)`` pair.

    This is the inverse of ``ply_from_move``. Raises ``ValueError`` if ``ply``
    is less than 1.
    """
    if ply < 1:
        raise ValueError("ply must be >= 1")
    move_number = (ply + 1) // 2
    side = "white" if ply % 2 == 1 else "black"
    return move_number, side


def derive_segments(annotation: Annotation) -> list[SegmentView]:
    """Build the list of ``SegmentView`` objects from an annotation's turning points.

    Each segment covers the ply range [turning_point, next_turning_point - 1], with
    the final segment extending to the last ply of the game. Raises ``ValueError`` if
    any turning point lies beyond the game's last ply.
    """
    last_ply = total_plies(annotation.pgn)
    turning_points = annotation.turning_points
    segments: list[SegmentView] = []

    for index, start_ply in enumerate(turning_points):
        if start_ply > last_ply:
            raise ValueError(
                f"Turning point {start_ply} is beyond the game's last ply {last_ply}"
            )
        # All segments except the last end one ply before the next turning point.
        if index < len(turning_points) - 1:
            end_ply = turning_points[index + 1] - 1
        else:
            # The final segment extends to the end of the game.
            end_ply = last_ply
        content = annotation.segment_contents.get(start_ply, SegmentContent())
        segments.append(
            SegmentView(
                turning_point_ply=start_ply,
                start_ply=start_ply,
                end_ply=end_ply,
                content=content,
            )
        )
    return segments


def segment_end_ply(annotation: Annotation, index: int) -> int:
    """Return the inclusive end ply for the derived segment at position ``index`` (0-based)."""
    return derive_segments(annotation)[index].end_ply


def find_segment_index(annotation: Annotation, ply: int) -> int:
    """Return the 0-based index of the derived segment that contains ``ply``.

    Raises ``ValueError`` if ``ply`` is outside the range ``[1, total_plies]``.
    """
    n = total_plies(annotation.pgn)
    if not (1 <= ply <= n):
        raise ValueError(f"Ply {ply} is out of range [1, {n}]")
    result = 0
    # Walk the turning points and keep updating result as long as the turning
    # point is still at or before the target ply.
    for i, start_ply in enumerate(annotation.turning_points):
        if start_ply <= ply:
            result = i
        else:
            break
    return result


def find_segment_by_turning_point(
    annotation: Annotation, turning_point_ply: int
) -> SegmentView:
    """Return the ``SegmentView`` whose turning point is ``turning_point_ply``.

    Raises ``ValueError`` if ``turning_point_ply`` is not a turning point in
    the annotation.
    """
    if turning_point_ply not in annotation.segment_contents:
        raise ValueError(f"No segment starts at ply {turning_point_ply}")
    index = annotation.turning_points.index(turning_point_ply)
    return derive_segments(annotation)[index]


def move_range_for_turning_point(
    annotation: Annotation, turning_point_ply: int
) -> tuple[int, int]:
    """Return the ``(start_ply, end_ply)`` pair for the segment at ``turning_point_ply``."""
    segment = find_segment_by_turning_point(annotation, turning_point_ply)
    return segment.start_ply, segment.end_ply


def san_move_range(pgn: str, start_ply: int, end_ply: int) -> str:
    """Return a human-readable move-range string for the ply span ``[start_ply, end_ply]``.

    White moves are formatted as ``N. Move``; black moves as ``N...Move``.
    When the span contains a single move the result is just that one move
    (no ``"to ..."`` suffix). Returns an empty string if the span contains
    no moves. Raises ``ValueError`` if the PGN cannot be parsed.

    Example output: ``"1. e4 to 5...Nf6"``
    """
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse PGN")

    board = game.board()
    first_san: str | None = None
    last_san: str | None = None

    for i, move in enumerate(game.mainline_moves()):
        ply = i + 1
        if ply < start_ply:
            # Advance the board to keep it in sync even for skipped plies.
            board.push(move)
            continue
        if ply > end_ply:
            break

        move_number = (ply - 1) // 2 + 1
        is_white = ply % 2 == 1
        san = board.san(move)
        formatted = f"{move_number}. {san}" if is_white else f"{move_number}...{san}"

        if first_san is None:
            first_san = formatted
        last_san = formatted
        board.push(move)

    if first_san is None:
        return ""
    # A single-move span needs no range suffix.
    if first_san == last_san:
        return first_san
    return f"{first_san} to {last_san}"


def format_move_list(pgn: str, start_ply: int, end_ply: int) -> str:
    """Return a space-separated SAN move list for the ply range ``[start_ply, end_ply]``.

    White moves are preceded by their move number (e.g. ``"1. e4"``). The first
    black move in a segment is preceded by an ellipsis number (e.g. ``"1...e5"``)
    to show which move it is; subsequent black moves within the same segment are
    written without a number. Raises ``ValueError`` if the PGN cannot be parsed.

    Example output: ``"1. e4 e5 2. Nf3 Nc6"``
    """
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse PGN")

    board = game.board()
    parts: list[str] = []
    first_in_segment = True

    for i, move in enumerate(game.mainline_moves()):
        ply = i + 1
        if ply < start_ply:
            # Keep the board state current even for moves before the segment.
            board.push(move)
            continue
        if ply > end_ply:
            break

        move_number = (ply - 1) // 2 + 1
        is_white = ply % 2 == 1
        san = board.san(move)

        if is_white:
            # Always include the move number for white moves.
            parts.append(f"{move_number}. {san}")
        elif first_in_segment:
            # The first black move in a segment gets an ellipsis prefix so the
            # reader knows which move number it corresponds to.
            parts.append(f"{move_number}...{san}")
        else:
            # Subsequent black moves in the same segment need no number.
            parts.append(san)

        first_in_segment = False
        board.push(move)

    return " ".join(parts)
