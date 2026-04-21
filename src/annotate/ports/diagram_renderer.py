"""Port definition for chessboard diagram rendering adapters.

Any adapter that produces SVG board diagrams must implement this protocol.
The application layer depends only on this interface, never on a concrete
renderer, keeping rendering technology swappable.
"""

from typing import Protocol

import chess


class DiagramRenderer(Protocol):
    """Protocol for services that convert board positions into SVG diagrams.

    Implementors receive a fully set-up :class:`chess.Board` and an orientation
    string and return a self-contained SVG document as a plain string.  The
    caller is responsible for embedding or scaling the returned SVG.
    """

    def render(self, board: chess.Board, orientation: str) -> str:
        """Return an SVG string representing ``board`` viewed from the given side.

        Args:
            board: The board position to render.  The board must already reflect
                the state *after* the move being illustrated.
            orientation: ``"white"`` to place White's pieces at the bottom of
                the diagram, ``"black"`` to place Black's pieces at the bottom.

        Returns:
            A self-contained SVG document string suitable for embedding in a
            PDF or writing directly to a file.
        """
        ...
