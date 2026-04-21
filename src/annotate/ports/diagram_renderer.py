# annotate.ports.diagram_renderer
from typing import Protocol

import chess


class DiagramRenderer(Protocol):
    def render(self, board: chess.Board, orientation: str) -> str:
        """Return an SVG string for the given board position and orientation."""
        ...
