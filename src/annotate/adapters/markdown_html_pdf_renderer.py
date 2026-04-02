# annotate.adapters.markdown_html_pdf_renderer
import io
from importlib.resources import files
from pathlib import Path

import chess
import chess.pgn
import mistune
import weasyprint

from annotate.adapters.python_chess_diagram_renderer import PythonChessDiagramRenderer
from annotate.domain.annotation import Annotation
from annotate.domain.model import segment_end_ply, total_plies
from annotate.ports.document_renderer import DocumentRenderer


def format_move_list(pgn: str, start_ply: int, end_ply: int) -> str:
    """Return a SAN move list string for the ply range ``[start_ply, end_ply]``.

    The result uses standard algebraic notation with correct move numbers.
    When the range begins on a black move an ellipsis suffix is added to
    the move number for the first token, e.g. ``5... Nc6 6. Bb5``.
    """
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = game.board()
    parts: list[str] = []
    first_in_segment = True

    for i, move in enumerate(game.mainline_moves()):
        ply = i + 1
        if ply < start_ply:
            board.push(move)
            continue
        if ply > end_ply:
            break

        move_number = (ply - 1) // 2 + 1
        is_white = ply % 2 == 1
        san = board.san(move)

        if is_white:
            parts.append(f"{move_number}. {san}")
        elif first_in_segment:
            parts.append(f"{move_number}... {san}")
        else:
            parts.append(san)

        first_in_segment = False
        board.push(move)

    return " ".join(parts)


def _build_markdown(annotation: Annotation, diagram_paths: dict[int, Path]) -> str:
    """Assemble the Markdown source document for ``annotation``."""
    lines: list[str] = []

    lines += [f"# {annotation.title}", ""]
    lines += [f'<p class="byline">{annotation.author} — {annotation.date}</p>', ""]
    lines += ["---", ""]

    for i, seg in enumerate(annotation.segments):
        lines += [f"## {seg.label}", ""]

        start_ply = seg.start_ply
        end_ply = segment_end_ply(annotation, i)
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
    cached as SVG files under ``store_dir/cache/<annotation_id>/``.
    """

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
            if not seg.label
        ]
        if missing:
            segments_str = ", ".join(str(n) for n in missing)
            raise ValueError(
                f"Cannot render: segment(s) {segments_str} have no label"
            )
        if total_plies(annotation.pgn) == 0:
            raise ValueError("Cannot render: PGN contains no moves")

        # Step 2 — Render diagrams
        cache_dir = Path(store_dir) / "cache" / annotation.annotation_id
        diagram_renderer = PythonChessDiagramRenderer()
        diagram_paths: dict[int, Path] = {}
        for i, seg in enumerate(annotation.segments):
            if seg.show_diagram:
                end_ply = segment_end_ply(annotation, i)
                diagram_paths[i] = diagram_renderer.render(
                    annotation.pgn,
                    end_ply,
                    annotation.diagram_orientation,
                    diagram_size,
                    cache_dir,
                )

        # Step 3 — Build Markdown
        markdown_str = _build_markdown(annotation, diagram_paths)

        # Step 4 — Convert to HTML
        html_str = _build_html(markdown_str, page_size)

        # Step 5 — Render to PDF
        weasyprint.HTML(string=html_str).write_pdf(output_path)
