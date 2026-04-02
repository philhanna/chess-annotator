from abc import ABC, abstractmethod


class DiagramRenderer(ABC):
    """Describe a service that renders a board position as a diagram file.

    Implementations take a PGN game plus a target ply and produce a
    rendered diagram artifact for that position, typically reusing a
    cache directory supplied by the caller. The interface is intentionally
    small so the rendering technology can change without affecting the
    domain or use-case layers.
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
        """Render the board at ``end_ply`` and return the resulting file path."""
        ...
