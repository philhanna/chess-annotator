# annotate.ports.document_renderer
from pathlib import Path
from typing import Protocol

from annotate.domain.render_model import RenderModel


class DocumentRenderer(Protocol):
    def render(self, model: RenderModel, output_path: Path, orientation: str = "white") -> None:
        """Render a RenderModel to a document at output_path."""
        ...
