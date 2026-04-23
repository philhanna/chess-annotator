"""ReportLab-based PDF rendering adapter.

This module is the concrete implementation of the
:class:`~render.ports.document_renderer.DocumentRenderer` protocol.  It
converts a :class:`~render.domain.render_model_data.RenderModel` into a
paginated LETTER-format PDF using the ReportLab Platypus layout engine.

Layout overview
---------------
The document is built as a linear list of ReportLab *flowables*:

1. **Title block** — player names as a bold centred heading, followed by an
   optional italic subtitle (event, date) and an optional opening name.
2. **Segments** — for each :class:`~render.domain.segment.Segment`: an
   optional centred board diagram with caption, a bold move-sequence line,
   and an optional italic commentary paragraph.

All text is HTML-escaped before being passed to ``Paragraph`` to prevent
ReportLab from misinterpreting special characters in player names or comments.
"""

import html
import io
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from svglib.svglib import svg2rlg

from render.adapters.chess_svg_diagram_renderer import ChessSvgDiagramRenderer
from render.domain.game_headers import GameHeaders
from render.domain.plied_move import PliedMove
from render.domain.render_model import (
    caption_text,
    moves_text,
    parse_all_pgn,
    parse_pgn,
    subtitle_text,
)
from render.domain.render_model_data import RenderModel
from render.domain.segment import Segment
from render.ports.diagram_renderer import DiagramRenderer

TEXT_WIDTH = 468.0  # 612 - 2×72 pt margins
MARGIN = 72.0
DIAGRAM_SIZE = 80 * mm  # fixed diagram size (~227 pt)


def build_styles() -> dict[str, ParagraphStyle]:
    """Create and return the paragraph styles used throughout the generated PDF.

    Returns a dictionary keyed by style name with the following entries:

    * ``"Title"`` — 16 pt Helvetica Bold, centred, 12 pt space after.  Used
      for the player-names heading at the top of the document.
    * ``"Subtitle"`` — 12 pt Helvetica Oblique, centred, 4 pt space after.
      Used for the event/date line and the opening name.
    * ``"Moves"`` — 12 pt Helvetica Bold, left-aligned, 6 pt space after.
      Used for the formatted move-sequence token run in each segment.
    * ``"Comment"`` — 12 pt Helvetica, left-aligned, 18 pt leading (1.5×),
      6 pt space after.  Used for prose commentary paragraphs.
    * ``"Caption"`` — 11 pt Helvetica Oblique, centred, 4 pt space after.
      Used for the "After N. Move" line below each board diagram.

    Returns:
        A fresh dictionary of :class:`reportlab.lib.styles.ParagraphStyle`
        instances.  A new dictionary is created on each call so callers can
        modify styles without affecting other render passes.
    """

    return {
        "Title":    ParagraphStyle("Title",
                        fontName="Helvetica-Bold", fontSize=16,
                        alignment=TA_CENTER, spaceAfter=12),
        "Subtitle": ParagraphStyle("Subtitle",
                        fontName="Helvetica-Oblique", fontSize=12,
                        alignment=TA_CENTER, spaceAfter=4),
        "Moves":    ParagraphStyle("Moves",
                        fontName="Helvetica-Bold", fontSize=12,
                        leading=18,
                        alignment=TA_LEFT, spaceAfter=6),
        "Comment":  ParagraphStyle("Comment",
                        fontName="Helvetica", fontSize=12,
                        leading=18,
                        alignment=TA_LEFT, spaceAfter=6),
        "Caption":  ParagraphStyle("Caption",
                        fontName="Helvetica-Oblique", fontSize=11,
                        alignment=TA_CENTER, spaceAfter=4),
    }


class ReportLabPdfRenderer:
    """Concrete :class:`~render.ports.document_renderer.DocumentRenderer` using ReportLab.

    Renders a :class:`~render.domain.render_model_data.RenderModel` to a
    paginated LETTER PDF via the ReportLab Platypus layout engine.  Board
    diagrams are produced by the injected
    :class:`~render.ports.diagram_renderer.DiagramRenderer` and converted
    from SVG to ReportLab ``Drawing`` objects by ``svglib``.
    """

    def __init__(self, diagram_renderer: DiagramRenderer) -> None:
        """Initialise the renderer with its diagram-rendering dependency.

        Args:
            diagram_renderer: An object satisfying the
                :class:`~render.ports.diagram_renderer.DiagramRenderer`
                protocol, used to produce SVG images for diagram moves.
        """

        self._diagram_renderer = diagram_renderer

    def render(
        self,
        model: RenderModel,
        output_path: Path,
        orientation: str = "white",
    ) -> None:
        """Build a PDF from a single ``model`` and write it to ``output_path``.

        Args:
            model: The parsed game data including headers and all segments.
            output_path: Destination path for the PDF file.  The file is
                created or overwritten; its parent directory must already exist.
            orientation: ``"white"`` or ``"black"`` — which side's perspective
                is used for all board diagrams.  Defaults to ``"white"``.
        """

        self.render_collection([model], output_path, orientation)

    def render_collection(
        self,
        models: list[RenderModel],
        output_path: Path,
        orientation: str = "white",
    ) -> None:
        """Build a PDF from one or more models and write it to ``output_path``.

        Each game starts on a new page after the first.

        Args:
            models: Ordered list of parsed games to render.
            output_path: Destination path for the PDF file.
            orientation: ``"white"`` or ``"black"`` — board diagram perspective.
        """

        styles = build_styles()
        story: list = []
        for i, model in enumerate(models):
            if i > 0:
                story.append(PageBreak())
            story.extend(self.title_flowables(model.headers, styles))
            if model.pre_game_comment:
                story.append(Paragraph(html.escape(model.pre_game_comment), styles["Comment"]))
            for segment in model.segments:
                story.extend(self.segment_flowables(segment, orientation, styles))
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=LETTER,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
        )
        doc.build(story)

    def title_flowables(self, headers: GameHeaders, styles: dict) -> list:
        """Build the ordered list of flowables for the document title block.

        Produces: player-names heading, optional event/date subtitle, optional
        opening name, then a 18 pt spacer before the first segment.

        Args:
            headers: Normalised game headers.
            styles: Paragraph style dictionary from :func:`build_styles`.

        Returns:
            A list of ReportLab flowables in layout order.
        """

        flowables: list = []
        player_line = html.escape(f"{headers.white} – {headers.black}")
        flowables.append(Paragraph(player_line, styles["Title"]))
        subtitle = subtitle_text(headers)
        if subtitle:
            flowables.append(Paragraph(html.escape(subtitle), styles["Subtitle"]))
        if headers.opening:
            flowables.append(Paragraph(html.escape(headers.opening), styles["Subtitle"]))
        flowables.append(Spacer(0, 18))
        return flowables

    def segment_flowables(
        self,
        segment: Segment,
        orientation: str,
        styles: dict,
    ) -> list:
        """Convert one commentary segment into its ordered list of flowables.

        Layout order within a segment: optional diagram block (diagram + caption
        + surrounding spacers), bold move-sequence paragraph, optional comment
        paragraph.

        Args:
            segment: The segment to render.
            orientation: Board orientation passed through to
                :meth:`diagram_flowables`.
            styles: Paragraph style dictionary from :func:`build_styles`.

        Returns:
            A list of ReportLab flowables in layout order.
        """

        flowables: list = []
        if segment.diagram_move is not None:
            flowables.extend(self.diagram_flowables(segment.diagram_move, orientation, styles))
        flowables.append(Paragraph(html.escape(moves_text(segment)), styles["Moves"]))
        if segment.comment:
            flowables.append(Paragraph(html.escape(segment.comment), styles["Comment"]))
        return flowables

    def diagram_flowables(
        self,
        diagram_move: PliedMove,
        orientation: str,
        styles: dict,
    ) -> list:
        """Render a single board diagram and caption as centred flowables.

        Converts the SVG produced by the diagram renderer into a ReportLab
        ``Drawing``, scales it to :data:`DIAGRAM_SIZE`, wraps it in a
        single-column ``Table`` to force centring within the text column, and
        appends a caption paragraph.

        If ``svglib`` fails to parse the SVG (returns ``None``), the diagram is
        skipped with a :func:`warnings.warn` call and an empty list is returned
        so the rest of the document renders normally.

        Args:
            diagram_move: The move whose ``diagram_board`` is to be rendered.
                ``diagram_move.diagram_board`` must not be ``None``.
            orientation: ``"white"`` or ``"black"`` — the viewing perspective
                for the diagram.
            styles: Paragraph style dictionary from :func:`build_styles`.

        Returns:
            ``[Spacer, Table(diagram), Caption, Spacer]`` on success, or
            ``[]`` when SVG conversion fails.
        """

        svg_text = self._diagram_renderer.render(diagram_move.diagram_board, orientation)
        drawing = svg2rlg(io.StringIO(svg_text))
        if drawing is None:
            import warnings
            warnings.warn(f"svglib failed to convert diagram at ply {diagram_move.ply}; skipping")
            return []

        scale = DIAGRAM_SIZE / drawing.width
        drawing.width = DIAGRAM_SIZE
        drawing.height = DIAGRAM_SIZE
        drawing.transform = (scale, 0, 0, scale, 0, 0)

        # Centre within the text column, which is itself centred on the page
        table = Table([[drawing]], colWidths=[TEXT_WIDTH])
        table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))

        caption = Paragraph(caption_text(diagram_move), styles["Caption"])
        return [Spacer(0, 12), table, caption, Spacer(0, 12)]


def render_pdf(
    pgn_text: str,
    output_path: Path,
    orientation: str = "white",
) -> None:
    """Parse PGN text and render a PDF using the default adapter stack.

    Convenience function that wires up the standard
    :class:`ChessSvgDiagramRenderer` and :class:`ReportLabPdfRenderer` and
    invokes the full pipeline in one call.  Suitable for use from scripts and
    tests that do not need to customise the adapter stack.

    Args:
        pgn_text: The full text of a PGN file.  Only the first game is used.
        output_path: Destination path for the PDF file.  The file is created
            or overwritten; its parent directory must already exist.
        orientation: ``"white"`` or ``"black"`` — the viewing perspective for
            all board diagrams.  Defaults to ``"white"``.

    Raises:
        ValueError: If ``pgn_text`` contains no parseable game.
    """
    models = parse_all_pgn(pgn_text)
    ReportLabPdfRenderer(diagram_renderer=ChessSvgDiagramRenderer()).render_collection(
        models, output_path, orientation
    )
