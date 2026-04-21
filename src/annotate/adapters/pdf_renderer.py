# annotate.adapters.pdf_renderer
import html
import io
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from svglib.svglib import svg2rlg

from annotate.adapters.chess_svg_diagram_renderer import ChessSvgDiagramRenderer
from annotate.domain.render_model import (
    GameHeaders,
    PliedMove,
    RenderModel,
    Segment,
    _caption_text,
    _moves_text,
    _subtitle_text,
    parse_pgn,
)
from annotate.ports.diagram_renderer import DiagramRenderer

TEXT_WIDTH = 468.0  # 612 - 2×72 pt margins
MARGIN = 72.0
DIAGRAM_SIZE = 80 * mm  # fixed diagram size (~227 pt)


def _build_styles() -> dict[str, ParagraphStyle]:
    return {
        "Title":    ParagraphStyle("Title",
                        fontName="Helvetica-Bold", fontSize=16,
                        alignment=TA_CENTER, spaceAfter=12),
        "Subtitle": ParagraphStyle("Subtitle",
                        fontName="Helvetica-Oblique", fontSize=12,
                        alignment=TA_CENTER, spaceAfter=4),
        "Moves":    ParagraphStyle("Moves",
                        fontName="Helvetica-Bold", fontSize=12,
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
    def __init__(self, diagram_renderer: DiagramRenderer) -> None:
        self._diagram_renderer = diagram_renderer

    def render(
        self,
        model: RenderModel,
        output_path: Path,
        orientation: str = "white",
    ) -> None:
        styles = _build_styles()
        story: list = []
        story.extend(self._title_flowables(model.headers, styles))
        for segment in model.segments:
            story.extend(self._segment_flowables(segment, orientation, styles))
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=LETTER,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
        )
        doc.build(story)

    def _title_flowables(self, headers: GameHeaders, styles: dict) -> list:
        flowables: list = []
        player_line = html.escape(f"{headers.white} – {headers.black}")
        flowables.append(Paragraph(player_line, styles["Title"]))
        subtitle = _subtitle_text(headers)
        if subtitle:
            flowables.append(Paragraph(html.escape(subtitle), styles["Subtitle"]))
        if headers.opening:
            flowables.append(Paragraph(html.escape(headers.opening), styles["Subtitle"]))
        flowables.append(Spacer(0, 18))
        return flowables

    def _segment_flowables(
        self,
        segment: Segment,
        orientation: str,
        styles: dict,
    ) -> list:
        flowables: list = []
        if segment.diagram_move is not None:
            flowables.extend(self._diagram_flowables(segment.diagram_move, orientation, styles))
        flowables.append(Paragraph(html.escape(_moves_text(segment)), styles["Moves"]))
        if segment.comment:
            flowables.append(Paragraph(html.escape(segment.comment), styles["Comment"]))
        return flowables

    def _diagram_flowables(
        self,
        diagram_move: PliedMove,
        orientation: str,
        styles: dict,
    ) -> list:
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

        caption = Paragraph(_caption_text(diagram_move), styles["Caption"])
        return [Spacer(0, 12), table, caption, Spacer(0, 12)]


def render_pdf(
    pgn_text: str,
    output_path: Path,
    orientation: str = "white",
) -> None:
    """Convenience wrapper: parse PGN and render to PDF using default adapters."""
    model = parse_pgn(pgn_text)
    ReportLabPdfRenderer(diagram_renderer=ChessSvgDiagramRenderer()).render(
        model, output_path, orientation
    )
