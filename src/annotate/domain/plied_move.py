"""Frozen value object describing one move in the render model."""

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class PliedMove:
    """Represents one move in the mainline plus any rendering metadata."""

    ply: int
    san: str
    nag_symbol: str | None
    diagram_board: chess.Board | None
    comment: str
    result: str | None = None
