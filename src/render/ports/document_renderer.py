"""Port definition for document rendering adapters.

Any adapter that serialises a :class:`RenderModel` to a file format (PDF,
HTML, etc.) must implement this protocol.  The application layer depends only
on this interface so that output formats can be swapped without touching domain
logic.
"""

from pathlib import Path
from typing import Protocol

from render.domain.render_model_data import RenderModel


class DocumentRenderer(Protocol):
    """Protocol implemented by adapters that write complete output documents.

    A document renderer takes the fully-parsed, format-agnostic
    :class:`RenderModel` and materialises it into a concrete file on disk.
    Callers must ensure ``output_path``'s parent directory exists before
    invoking :meth:`render`.
    """

    def render(self, model: RenderModel, output_path: Path, orientation: str = "white") -> None:
        """Write a complete document for ``model`` to ``output_path``.

        Args:
            model: The parsed game data to render, including headers and all
                commentary segments.
            output_path: Destination file path.  The file is created or
                overwritten; the parent directory must already exist.
            orientation: ``"white"`` to show diagrams from White's perspective,
                ``"black"`` to show them from Black's perspective.
                Defaults to ``"white"``.
        """
        ...
