
from abc import ABC, abstractmethod


class DiagramRenderer(ABC):

    @abstractmethod
    def render(
        self,
        pgn: str,
        end_ply: int,
        orientation: str,
        size: int,
        cache_dir,
    ):
        """Render the board at end_ply to an SVG file and return its Path."""
        ...
