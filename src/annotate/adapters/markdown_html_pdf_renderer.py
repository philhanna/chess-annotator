from importlib.resources import files
from pathlib import Path

import mistune
import weasyprint

from annotate.adapters.python_chess_diagram_renderer import PythonChessDiagramRenderer
from annotate.domain.annotation import Annotation
from annotate.domain.model import format_move_list, total_plies
from annotate.ports.document_renderer import DocumentRenderer


def _build_markdown(annotation: Annotation, diagram_paths: dict[int, Path]) -> str:
    """Assemble the Markdown source document for ``annotation``.

    Produces a document with a top-level title, an author/date byline, and one
    ``##``-level section per segment. Each section contains the segment move list,
    optional annotation text, and an optional inline SVG diagram.

    Args:
        annotation:    The annotation to render.
        diagram_paths: Map from 0-based segment index to the rendered SVG file
                       path for that segment. Only segments whose index appears
                       in this dict will have a diagram included.
    """
    lines: list[str] = []

    # Document header: title and byline.
    lines += [f"# {annotation.title}", ""]
    lines += [f'<p class="byline">{annotation.author} — {annotation.date}</p>', ""]
    lines += ["---", ""]

    for i, seg in enumerate(annotation.segments):
        # Section heading from the segment label.
        lines += [f"## {seg.label}", ""]

        start_ply = seg.start_ply
        end_ply = seg.end_ply
        move_list = format_move_list(annotation.pgn, start_ply, end_ply)
        lines += [f'<code class="move-list">{move_list}</code>', ""]

        # Annotation text (only if the author wrote something).
        if seg.commentary.strip():
            lines += [seg.commentary.strip(), ""]

        # Inline SVG diagram (only if enabled and a path was rendered).
        if seg.show_diagram and i in diagram_paths:
            lines += [diagram_paths[i].read_text(), ""]

        lines += ["---", ""]

    return "\n".join(lines)


def _build_html(body_markdown: str, page_size: str) -> str:
    """Convert Markdown source to a complete HTML document with embedded CSS.

    Reads the ``chess_book.css`` stylesheet from the package data and inlines
    it into a ``<style>`` block. The ``@page`` rule is generated dynamically
    to honour the requested ``page_size``.

    Args:
        body_markdown: Markdown string produced by ``_build_markdown``.
        page_size:     ``"a4"`` or any other value (treated as ``"letter"``).
    """
    md = mistune.create_markdown()
    body_html = md(body_markdown)

    # Load the bundled stylesheet from the package data directory.
    css = files("annotate.adapters").joinpath("chess_book.css").read_text()
    page_size_css = "A4" if page_size.lower() == "a4" else "letter"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{
    size: {page_size_css};
    margin: 2.5cm;
}}
@page {{
    @bottom-center {{
        content: counter(page);
        font-size: 10pt;
        font-family: Georgia, serif;
    }}
}}
{css}
</style>
</head>
<body>
{body_html}
</body>
</html>"""


class MarkdownHTMLPDFRenderer(DocumentRenderer):
    """Render an annotation to a book-quality PDF via a Markdown → HTML → PDF pipeline.

    The pipeline has five stages:

    1. **Validate** — check that every segment has a non-blank label and annotation.
    2. **Render diagrams** — produce SVG files for segments with ``show_diagram=True``,
       caching them under ``<store_dir>/<game_id>/diagram-cache/``.
    3. **Build Markdown** — assemble the full document source from segments and diagrams.
    4. **Convert to HTML** — render the Markdown to HTML with embedded CSS.
    5. **Render to PDF** — use WeasyPrint to write the final PDF file.
    """

    def __init__(self, diagram_renderer=None) -> None:
        """Initialise the renderer, optionally supplying a custom diagram renderer.

        Args:
            diagram_renderer: A ``DiagramRenderer`` instance to use for board diagrams.
                              Defaults to ``PythonChessDiagramRenderer`` if not provided.
        """
        self.diagram_renderer = diagram_renderer or PythonChessDiagramRenderer()

    def render(
        self,
        annotation: Annotation,
        output_path: Path,
        diagram_size: int,
        page_size: str,
        store_dir: Path,
    ) -> None:
        """Render ``annotation`` to a PDF at ``output_path``.

        Args:
            annotation:   The annotation to render. Every segment must have a
                          non-blank label and annotation text.
            output_path:  Destination path for the PDF file. Parent directories
                          are created automatically.
            diagram_size: Width (and height) in pixels for board diagrams.
            page_size:    Paper size, either ``"a4"`` or ``"letter"``.
            store_dir:    Root store directory, used to locate the diagram cache.

        Raises:
            ValueError: if any segment is missing a label or annotation text, or
                        if the PGN contains no moves.
        """
        # Step 1 — Validate: every segment must have both a label and annotation.
        missing = [
            i + 1
            for i, seg in enumerate(annotation.segments)
            if not seg.label.strip() or not seg.commentary.strip()
        ]
        if missing:
            segments_str = ", ".join(str(n) for n in missing)
            raise ValueError(
                "Cannot render: segment(s) "
                f"{segments_str} must have both label and annotation"
            )
        if total_plies(annotation.pgn) == 0:
            raise ValueError("Cannot render: PGN contains no moves")

        # Step 2 — Render diagrams into the game's diagram cache directory.
        cache_dir = Path(store_dir) / annotation.game_id / "diagram-cache"
        diagram_paths: dict[int, Path] = {}
        for i, seg in enumerate(annotation.segments):
            if seg.show_diagram:
                diagram_paths[i] = self.diagram_renderer.render(
                    annotation.pgn,
                    seg.end_ply,
                    annotation.diagram_orientation,
                    diagram_size,
                    cache_dir,
                )

        # Step 3 — Build the Markdown source document.
        markdown_str = _build_markdown(annotation, diagram_paths)

        # Step 4 — Convert Markdown to a full HTML document.
        html_str = _build_html(markdown_str, page_size)

        # Step 5 — Render the HTML to PDF via WeasyPrint.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        weasyprint.HTML(string=html_str).write_pdf(output_path)
