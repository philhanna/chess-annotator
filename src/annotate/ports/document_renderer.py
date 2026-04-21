"""Port definition for document rendering adapters."""

from pathlib import Path
from typing import Protocol

from annotate.domain.render_model import RenderModel


class DocumentRenderer(Protocol):
    """Protocol implemented by adapters that render complete output documents."""

    def render(self, model: RenderModel, output_path: Path, orientation: str = "white") -> None:
        """Render ``model`` to ``output_path`` using the requested orientation."""
        ...
