"""SVG diagram renderer backed by python-chess.

This module is the concrete implementation of the
:class:`~render.ports.diagram_renderer.DiagramRenderer` protocol.  It wraps
``chess.svg.board`` and applies cosmetic post-processing to produce clean,
print-quality SVG diagrams.
"""

import re

import chess
import chess.svg

BOARD_COLORS = {
    "margin": "#ffffff",
    "coord": "#000000",
    "inner border": "#ffffff",
    "outer border": "#ffffff",
}
COORDINATE_GROUP = re.compile(
    r'(<g transform="translate\([^"]+\) scale\(0\.75, 0\.75\)" fill="#000000") stroke="#000000">',
)


class ChessSvgDiagramRenderer:
    """Concrete :class:`~render.ports.diagram_renderer.DiagramRenderer` backed by python-chess.

    Produces 300 px SVG board diagrams with a white margin and no border, then
    removes the stroke from coordinate glyphs so rank and file labels render
    with the same weight as other text rather than appearing artificially bold.
    """

    def render(self, board: chess.Board, orientation: str) -> str:
        """Return an SVG board diagram with the requested side at the bottom.

        Args:
            board: The board position to render, already advanced to the state
                after the move being illustrated.
            orientation: ``"white"`` to place White's pieces at the bottom,
                ``"black"`` to place Black's pieces at the bottom.

        Returns:
            A self-contained SVG string at 300 px with coordinate labels and a
            white background, ready for embedding in a ReportLab document via
            ``svglib``.
        """

        chess_orientation = chess.WHITE if orientation == "white" else chess.BLACK
        svg = chess.svg.board(
            board,
            orientation=chess_orientation,
            size=300,
            colors=BOARD_COLORS,
        )
        # python-chess outlines coordinate glyphs with the same color as the fill,
        # which makes the border labels look bold. Removing that stroke keeps them crisp.
        return COORDINATE_GROUP.sub('\\1 stroke="none">', svg)
