"""Frozen value object describing one rendered commentary segment.

A segment is a run of contiguous mainline moves that share a single leading
comment.  The PGN is split into segments at every move that carries a comment:
that comment belongs to the segment it opens, not to the preceding one.
Moves without any comment form part of the same segment as the previous
commented move, or a leading uncommented segment if the game begins without
a comment.
"""

from __future__ import annotations

from dataclasses import dataclass

from annotate.domain.plied_move import PliedMove


@dataclass(frozen=True)
class Segment:
    """A contiguous run of moves introduced by a single commentary block.

    Renderers lay out each segment as: optional diagram, move sequence, then
    comment prose.  If no comment is present the prose block is omitted; if no
    move in the segment carries NAG 220 the diagram is omitted.

    Attributes:
        moves: The ordered half-moves belonging to this segment.  Always
            non-empty; the first move is the one whose PGN comment opened the
            segment.
        comment: The prose commentary for this segment, taken from the first
            move's PGN comment.  Empty string when the segment has no leading
            comment (e.g. the opening moves before the first annotation).
        diagram_move: The move within ``moves`` that was marked with NAG 220
            and therefore requests a board diagram, or ``None`` if no such move
            exists.  When multiple moves in the same segment carry NAG 220 only
            the first is used.
    """

    moves: tuple[PliedMove, ...]
    comment: str
    diagram_move: PliedMove | None
