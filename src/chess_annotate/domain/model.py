# chess_annotate.domain.model

import io
import uuid
from dataclasses import dataclass, field

import chess.pgn


@dataclass
class Segment:
    start_ply: int
    label: str | None = None
    commentary: str = ""
    show_diagram: bool = False


@dataclass
class Annotation:
    annotation_id: str
    title: str
    author: str
    date: str                   # ISO 8601
    pgn: str
    player_side: str            # "white" | "black" | "none"
    diagram_orientation: str    # "white" | "black"
    segments: list[Segment] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        title: str,
        author: str,
        date: str,
        pgn: str,
        player_side: str,
        diagram_orientation: str | None = None,
    ) -> "Annotation":
        if diagram_orientation is None:
            diagram_orientation = "black" if player_side == "black" else "white"
        annotation_id = str(uuid.uuid4())
        initial_segment = Segment(start_ply=1)
        return cls(
            annotation_id=annotation_id,
            title=title,
            author=author,
            date=date,
            pgn=pgn,
            player_side=player_side,
            diagram_orientation=diagram_orientation,
            segments=[initial_segment],
        )


# ---------------------------------------------------------------------------
# Business-rule functions
# ---------------------------------------------------------------------------

def total_plies(pgn: str) -> int:
    """Return the number of half-moves (plies) in the main line of a PGN."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse PGN")
    return sum(1 for _ in game.mainline_moves())


def ply_from_move(move_number: int, side: str) -> int:
    """Convert move-number + side to a 1-based ply index.

    Examples:
        move 1 white → ply 1
        move 1 black → ply 2
        move 2 white → ply 3
    """
    if side not in ("white", "black"):
        raise ValueError(f"side must be 'white' or 'black', got {side!r}")
    side_offset = 1 if side == "white" else 2
    return (move_number - 1) * 2 + side_offset


def move_from_ply(ply: int) -> tuple[int, str]:
    """Convert a 1-based ply index to (move_number, side).

    Examples:
        ply 1 → (1, "white")
        ply 2 → (1, "black")
        ply 3 → (2, "white")
    """
    move_number = (ply - 1) // 2 + 1
    side = "white" if ply % 2 == 1 else "black"
    return move_number, side


def segment_end_ply(annotation: Annotation, index: int) -> int:
    """Return the last ply (inclusive) of the segment at *index*."""
    segments = annotation.segments
    if index < len(segments) - 1:
        return segments[index + 1].start_ply - 1
    return total_plies(annotation.pgn)


def find_segment_index(annotation: Annotation, ply: int) -> int:
    """Return the index of the segment that contains *ply*.

    Raises ValueError if ply is out of range.
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
