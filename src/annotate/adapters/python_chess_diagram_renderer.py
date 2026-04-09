import io
from pathlib import Path

import chess
import chess.pgn
import chess.svg

from annotate.ports.diagram_renderer import DiagramRenderer


class PythonChessDiagramRenderer(DiagramRenderer):
    """Render board positions as SVG files using ``python-chess``.

    Diagrams are cached under ``<cache_dir>/<end_ply>-<orientation>.svg``. If the
    file already exists for a requested position it is returned immediately without
    re-rendering, so repeated calls for the same position are essentially free.
    The cache directory is created on demand if it does not already exist.
    """

    def render(
        self,
        pgn: str,
        end_ply: int,
        orientation: str,
        size: int,
        cache_dir: Path,
    ) -> Path:
        """Render the board after ``end_ply`` half-moves and return the SVG file path.

        Args:
            pgn:         PGN string for the game.
            end_ply:     1-based ply index; the board is shown after this move.
            orientation: ``"white"`` or ``"black"`` — which side appears at the bottom.
            size:        Width (and height) in pixels for the SVG output.
            cache_dir:   Directory used to cache rendered SVG files.

        Returns:
            Path to the SVG file (either freshly rendered or retrieved from cache).
        """
        cache_dir = Path(cache_dir)
        # Cache file name encodes both the ply and orientation to avoid collisions.
        svg_path = cache_dir / f"{end_ply}-{orientation}.svg"
        if svg_path.exists():
            # Cache hit — return without re-rendering.
            return svg_path

        # Parse the game and advance the board to the requested ply.
        game = chess.pgn.read_game(io.StringIO(pgn))
        board = game.board()
        for i, move in enumerate(game.mainline_moves()):
            board.push(move)
            if i + 1 == end_ply:
                break

        # Convert the orientation string to the python-chess colour constant.
        chess_orientation = chess.BLACK if orientation == "black" else chess.WHITE
        svg_content = chess.svg.board(board, orientation=chess_orientation, size=size)

        # Write the SVG to the cache directory, creating it first if needed.
        cache_dir.mkdir(parents=True, exist_ok=True)
        svg_path.write_text(svg_content)
        return svg_path
