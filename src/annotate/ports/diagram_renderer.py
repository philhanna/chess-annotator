"""Port definition for chessboard diagram rendering adapters."""

from typing import Protocol

import chess


class DiagramRenderer(Protocol):
    """Protocol for services that turn board positions into SVG diagrams."""

    def render(self, board: chess.Board, orientation: str) -> str:
        """Return an SVG string for ``board`` with the chosen orientation."""
        ...
