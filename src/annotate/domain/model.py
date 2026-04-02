
import io

import chess.pgn

from annotate.domain.annotation import Annotation
from annotate.domain.segment import Segment


# ---------------------------------------------------------------------------
# Business-rule functions
# ---------------------------------------------------------------------------

def total_plies(pgn: str) -> int:
    """Count the plies in the main line of a PGN game.

    The function parses ``pgn`` with ``python-chess`` and counts only
    the moves in the main line, ignoring side variations. A
    ``ValueError`` is raised when the PGN cannot be parsed into a game.
    """
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse PGN")
    return sum(1 for _ in game.mainline_moves())


def ply_from_move(move_number: int, side: str) -> int:
    """Convert move-number plus side into a 1-based ply index.

    This is the application's internal indexing scheme for locating
    positions within a game. ``side`` must be either ``"white"`` or
    ``"black"``; any other value raises ``ValueError``.

    Examples:
        move 1 white -> ply 1
        move 1 black -> ply 2
        move 2 white -> ply 3
    """
    if side not in ("white", "black"):
        raise ValueError(f"side must be 'white' or 'black', got {side!r}")
    side_offset = 1 if side == "white" else 2
    return (move_number - 1) * 2 + side_offset


def move_from_ply(ply: int) -> tuple[int, str]:
    """Convert a 1-based ply index back to move number and side.

    The returned tuple is the author-facing representation used by the
    CLI and rendering layers. The first element is the move number and
    the second is either ``"white"`` or ``"black"``.

    Examples:
        ply 1 -> (1, "white")
        ply 2 -> (1, "black")
        ply 3 -> (2, "white")
    """
    move_number = (ply - 1) // 2 + 1
    side = "white" if ply % 2 == 1 else "black"
    return move_number, side


def segment_end_ply(annotation: Annotation, index: int) -> int:
    """Return the inclusive end ply for a segment in an annotation.

    Segment end boundaries are derived rather than stored. For any
    non-final segment, the end is the ply immediately before the next
    segment starts. For the final segment, the end is the final ply in
    the game's main line.
    """
    segments = annotation.segments
    if index < len(segments) - 1:
        return segments[index + 1].start_ply - 1
    return total_plies(annotation.pgn)


def find_segment_index(annotation: Annotation, ply: int) -> int:
    """Locate the segment index that contains a given ply.

    The search assumes segments are ordered by ascending ``start_ply``,
    which is the invariant maintained by the domain model. A
    ``ValueError`` is raised when ``ply`` falls outside the valid range
    of the annotation's PGN.
    """
    n = total_plies(annotation.pgn)
    if not (1 <= ply <= n):
        raise ValueError(f"Ply {ply} is out of range [1, {n}]")
    # Segments are ordered by start_ply ascending.
    # The containing segment is the last one whose start_ply <= ply.
    result = 0
    for i, seg in enumerate(annotation.segments):
        if seg.start_ply <= ply:
            result = i
        else:
            break
    return result
