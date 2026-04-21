"""Frozen value object describing one move in the render model.

A ply is a single half-move (one side's turn).  Ply 1 is White's first move,
ply 2 is Black's first reply, and so on.  The move number shown in notation is
``(ply + 1) // 2``.
"""

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class PliedMove:
    """One mainline half-move together with its rendering annotations.

    Instances are produced by :func:`~render.domain.render_model.collect_moves`
    and consumed by formatters and diagram builders.  The dataclass is frozen so
    that segment tuples remain hashable and immutable throughout the pipeline.

    Attributes:
        ply: Half-move counter starting at 1.  Odd plies are White's moves,
            even plies are Black's moves.
        san: Standard Algebraic Notation for the move (e.g. ``"Nf3"``), without
            any NAG suffix — the suffix lives in ``nag_symbol``.
        nag_symbol: Human-readable symbol derived from the PGN NAG (Numeric
            Annotation Glyph), such as ``"!"`` (good move), ``"?"`` (mistake),
            ``"!!"`` (brilliant), ``"??"`` (blunder), ``"!?"`` (interesting),
            or ``"?!"`` (dubious).  ``None`` if no recognised NAG is present.
        diagram_board: A snapshot of the board position *after* this move,
            present only when the PGN marks the move with NAG 220 to request a
            diagram.  The board is copied at parse time so later traversal
            cannot mutate it.  ``None`` when no diagram is requested.
        comment: The PGN comment attached to this move, stripped of leading and
            trailing whitespace.  Empty string when there is no comment.
        result: The PGN result string (``"1-0"``, ``"0-1"``, or ``"1/2-1/2"``)
            appended to the final move of the game.  ``None`` for all other
            moves, and ``None`` when the result is unknown (``"*"``).
    """

    ply: int
    san: str
    nag_symbol: str | None
    diagram_board: chess.Board | None
    comment: str
    result: str | None = None
