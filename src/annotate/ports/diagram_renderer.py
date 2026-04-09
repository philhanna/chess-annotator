from abc import ABC, abstractmethod


class DiagramRenderer(ABC):
    """Port for rendering a chess board position to a diagram file.

    Implementations take a PGN game string, advance to the requested ply, and
    produce a diagram file (typically an SVG) in a caller-supplied cache directory.
    The rendering technology can change without affecting the domain or use-case
    layers.
    """

    @abstractmethod
    def render(
        self,
        pgn: str,
        end_ply: int,
        orientation: str,
        size: int,
        cache_dir,
    ):
        """Render the board position after ``end_ply`` half-moves and return the file path.

        Args:
            pgn:         PGN string of the game to render.
            end_ply:     1-based ply index; the board is shown after this move.
            orientation: ``"white"`` or ``"black"`` — which side appears at the bottom.
            size:        Width (and height) in pixels for the diagram image.
            cache_dir:   Directory in which the rendered file should be cached.

        Returns:
            Path to the rendered diagram file.
        """
        ...
