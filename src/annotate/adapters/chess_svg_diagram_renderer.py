"""SVG diagram renderer backed by python-chess."""

import chess
import chess.svg


class ChessSvgDiagramRenderer:
    """Render chess boards to SVG for downstream document generation."""

    def render(self, board: chess.Board, orientation: str) -> str:
        """Return an SVG board diagram with the requested side at the bottom."""

        chess_orientation = chess.WHITE if orientation == "white" else chess.BLACK
        return chess.svg.board(board, orientation=chess_orientation, size=300)
