"""Board SVG rendering adapter for the annotate application."""

from __future__ import annotations

import chess
import chess.svg


class SvgBoardRenderer:
    """Render board SVG for a given FEN position."""

    def __init__(self, size: int = 480) -> None:
        self._size = size

    def render(self, fen: str, lastmove: chess.Move | None = None) -> str:
        """Return SVG markup for the provided board position."""

        board = chess.Board(fen)
        check = board.king(board.turn) if board.is_check() else None
        return chess.svg.board(
            board=board,
            size=self._size,
            lastmove=lastmove,
            check=check,
        )
