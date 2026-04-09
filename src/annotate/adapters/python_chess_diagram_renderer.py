import io
from pathlib import Path

import chess
import chess.pgn
import chess.svg

from annotate.ports.diagram_renderer import DiagramRenderer


class PythonChessDiagramRenderer(DiagramRenderer):
    def render(
        self,
        pgn: str,
        end_ply: int,
        orientation: str,
        size: int,
        cache_dir: Path,
    ) -> Path:
        cache_dir = Path(cache_dir)
        svg_path = cache_dir / f"{end_ply}-{orientation}.svg"
        if svg_path.exists():
            return svg_path

        game = chess.pgn.read_game(io.StringIO(pgn))
        board = game.board()
        for i, move in enumerate(game.mainline_moves()):
            board.push(move)
            if i + 1 == end_ply:
                break

        chess_orientation = chess.BLACK if orientation == "black" else chess.WHITE
        svg_content = chess.svg.board(board, orientation=chess_orientation, size=size)

        cache_dir.mkdir(parents=True, exist_ok=True)
        svg_path.write_text(svg_content)
        return svg_path
