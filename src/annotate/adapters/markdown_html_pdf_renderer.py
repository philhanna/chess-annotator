from importlib.resources import files
from pathlib import Path

import mistune
import weasyprint

from annotate.adapters.python_chess_diagram_renderer import PythonChessDiagramRenderer
from annotate.domain.annotation import Annotation
from annotate.domain.model import format_move_list, total_plies
from annotate.ports.document_renderer import DocumentRenderer


def _build_markdown(annotation: Annotation, diagram_paths: dict[int, Path]) -> str:
    """Assemble the Markdown source document for ``annotation``."""
    lines: list[str] = []

    lines += [f"# {annotation.title}", ""]
    lines += [f'<p class="byline">{annotation.author} — {annotation.date}</p>', ""]
    lines += ["---", ""]

    for i, seg in enumerate(annotation.segments):
        lines += [f"## {seg.label}", ""]

        start_ply = seg.start_ply
        end_ply = seg.end_ply
        move_list = format_move_list(annotation.pgn, start_ply, end_ply)
        lines += [f'<code class="move-list">{move_list}</code>', ""]

        if seg.commentary.strip():
            lines += [seg.commentary.strip(), ""]

        if seg.show_diagram and i in diagram_paths:
            lines += [diagram_paths[i].read_text(), ""]

        lines += ["---", ""]

    return "\n".join(lines)


def _build_html(body_markdown: str, page_size: str) -> str:
    """Convert Markdown to a full HTML document with embedded CSS."""
    md = mistune.create_markdown()
    body_html = md(body_markdown)

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
    """Render an annotation to PDF via a Markdown → HTML → PDF pipeline.

    The pipeline has five stages: validation, diagram rendering, Markdown
    assembly, HTML conversion, and PDF output via WeasyPrint. Diagrams are
    cached as SVG files under ``<store_dir>/<game-id>/diagram-cache/``.
    """

    def __init__(self, diagram_renderer=None) -> None:
        self.diagram_renderer = diagram_renderer or PythonChessDiagramRenderer()

    def render(
        self,
        annotation: Annotation,
        output_path: Path,
        diagram_size: int,
        page_size: str,
        store_dir: Path,
    ) -> None:
        """Render ``annotation`` to a PDF at ``output_path``."""
        # Step 1 — Validate
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

        # Step 2 — Render diagrams
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

        # Step 3 — Build Markdown
        markdown_str = _build_markdown(annotation, diagram_paths)

        # Step 4 — Convert to HTML
        html_str = _build_html(markdown_str, page_size)

        # Step 5 — Render to PDF
        output_path.parent.mkdir(parents=True, exist_ok=True)
        weasyprint.HTML(string=html_str).write_pdf(output_path)
