# annotate.adapters.chess_svg_diagram_renderer
import chess
import chess.svg


class ChessSvgDiagramRenderer:
    def render(self, board: chess.Board, orientation: str) -> str:
        chess_orientation = chess.WHITE if orientation == "white" else chess.BLACK
        return chess.svg.board(board, orientation=chess_orientation, size=300)
