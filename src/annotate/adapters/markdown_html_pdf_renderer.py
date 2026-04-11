import re
from importlib.resources import files
from pathlib import Path

import mistune
import weasyprint

from annotate.adapters.python_chess_diagram_renderer import PythonChessDiagramRenderer
from annotate.domain.annotation import Annotation
from annotate.domain.model import (
    format_move_list,
    game_headers,
    parse_diagram_tokens,
    san_move_range,
    total_plies,
)
from annotate.ports.document_renderer import DocumentRenderer

# Matches [[diagram <move><side> [<orientation>]]] tokens in annotation text.
_DIAGRAM_TOKEN_RE = re.compile(
    r"\[\[diagram\s+(\d+)(w|b)(?:\s+(white|black))?\]\]"
)


def _substitute_diagram_tokens(
    annotation_text: str,
    diagram_paths: dict[tuple[int, str], Path],
    pgn: str,
) -> str:
    """Replace ``[[diagram ...]]`` tokens in ``annotation_text`` with inline SVG figures.

    Each token is replaced with a ``<figure>`` block containing the rendered SVG
    and a caption. Tokens whose ``(ply, orientation)`` key is absent from
    ``diagram_paths`` are left in place unchanged.
    """
    from annotate.domain.model import ply_from_move

    def replace_token(m: re.Match) -> str:
        move_number = int(m.group(1))
        side = "white" if m.group(2) == "w" else "black"
        orientation = m.group(3) or "white"
        try:
            ply = ply_from_move(move_number, side)
        except ValueError:
            return m.group(0)
        path = diagram_paths.get((ply, orientation))
        if path is None:
            return m.group(0)
        caption = san_move_range(pgn, ply, ply)
        svg = path.read_text()
        return (
            f'\n<figure class="diagram">\n'
            f"{svg}\n"
            f"<figcaption>After {caption}</figcaption>\n"
            f"</figure>\n"
        )

    return _DIAGRAM_TOKEN_RE.sub(replace_token, annotation_text)


def _build_markdown(
    annotation: Annotation,
    diagram_paths: dict[tuple[int, str], Path],
) -> str:
    """Assemble the Markdown source document for ``annotation``.

    Produces a document with a top-level title, an author/date byline, and one
    ``##``-level section per segment. Each section contains the segment move list
    and the annotation text, with any ``[[diagram ...]]`` tokens replaced inline
    by SVG board diagrams.

    Args:
        annotation:    The annotation to render.
        diagram_paths: Map from ``(ply, orientation)`` pairs to the rendered SVG
                       file path for that position. Built by the render pipeline
                       from the tokens found in each segment's annotation text.
    """
    lines: list[str] = []

    # Document header: title and byline.
    lines += [f"# {annotation.title}", ""]
    lines += [f'<p class="byline">{annotation.author}</p>', ""]
    headers = game_headers(annotation.pgn)
    event = headers.get("Event", "")
    site = headers.get("Site", "")
    event_str = event if event and event != "?" else ""
    site_str = site if site and site != "?" else ""
    event_site = ", ".join(part for part in [event_str, site_str] if part)
    if event_site:
        lines += [f'<p class="event-site">{event_site}</p>', ""]
    lines += ["---", ""]

    for seg in annotation.segments:
        # Section heading from the segment label.
        lines += [f"## {seg.label}", ""]

        move_list = format_move_list(annotation.pgn, seg.start_ply, seg.end_ply)
        lines += [f'<code class="move-list">{move_list}</code>', ""]

        # Annotation text with diagram tokens substituted inline.
        if seg.commentary.strip():
            substituted = _substitute_diagram_tokens(
                seg.commentary.strip(), diagram_paths, annotation.pgn
            )
            lines += [substituted, ""]

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
    # This renderer intentionally embeds raw HTML and inline SVG in the Markdown
    # document, so HTML escaping must be disabled here.
    md = mistune.create_markdown(escape=False)
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
    2. **Render diagrams** — scan all annotation texts for ``[[diagram ...]]`` tokens,
       then render one SVG per unique ``(ply, orientation)`` pair into the game's
       ``diagram-cache/`` directory.
    3. **Build Markdown** — assemble the full document source, substituting each
       token inline with its rendered SVG figure block.
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

        # Step 2 — Render diagrams referenced by tokens in annotation texts.
        cache_dir = Path(store_dir) / annotation.game_id / "diagram-cache"
        diagram_paths: dict[tuple[int, str], Path] = {}
        for seg in annotation.segments:
            for token in parse_diagram_tokens(seg.annotation):
                key = (token.ply, token.orientation)
                if key not in diagram_paths:
                    diagram_paths[key] = self.diagram_renderer.render(
                        annotation.pgn,
                        token.ply,
                        token.orientation,
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
