"""SVG diagram renderer backed by python-chess."""

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
    """Render chess boards to SVG for downstream document generation."""

    def render(self, board: chess.Board, orientation: str) -> str:
        """Return an SVG board diagram with the requested side at the bottom."""

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
