# annotate.adapters.pdf_renderer
import calendar
import html
import io
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.pgn
import chess.svg
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from svglib.svglib import svg2rlg

NAG_SYMBOLS = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}
NAG_DIAGRAM = 220

TEXT_WIDTH = 468.0  # 612 - 2×72 pt margins
MARGIN = 72.0
DIAGRAM_SIZE = 80 * mm  # fixed diagram size (~227 pt)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PliedMove:
    ply: int
    san: str
    nag_symbol: str | None
    diagram_board: chess.Board | None
    comment: str


@dataclass(frozen=True)
class GameHeaders:
    white: str
    black: str
    event: str
    date: str
    opening: str


@dataclass(frozen=True)
class Segment:
    moves: tuple
    comment: str
    diagram_move: PliedMove | None


@dataclass(frozen=True)
class RenderModel:
    headers: GameHeaders
    segments: tuple


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _format_date(raw: str) -> str:
    parts = raw.split(".")
    if len(parts) != 3:
        return ""
    year_s, month_s, day_s = parts
    year = None if "?" in year_s else int(year_s)
    month = None if "?" in month_s else int(month_s)
    day = None if "?" in day_s else int(day_s)
    if year is None:
        return ""
    if month is None:
        return str(year)
    if day is None:
        return f"{calendar.month_abbr[month]} {year}"
    return f"{day:02d} {calendar.month_abbr[month]} {year}"


def _parse_headers(game: chess.pgn.Game) -> GameHeaders:
    def _tag(name: str) -> str:
        val = game.headers.get(name, "")
        return "" if val == "?" else val

    return GameHeaders(
        white=_tag("White"),
        black=_tag("Black"),
        event=_tag("Event"),
        date=_tag("Date"),
        opening=game.headers.get("Opening", ""),
    )


def _collect_moves(game: chess.pgn.Game) -> list[PliedMove]:
    moves = []
    node = game
    while node.variations:
        node = node.variations[0]
        nag_symbol = next((NAG_SYMBOLS[n] for n in node.nags if n in NAG_SYMBOLS), None)
        has_diagram = NAG_DIAGRAM in node.nags
        diagram_board = node.board().copy() if has_diagram else None
        moves.append(PliedMove(
            ply=node.ply(),
            san=node.san(),
            nag_symbol=nag_symbol,
            diagram_board=diagram_board,
            comment=node.comment.strip(),
        ))
    return moves


def _build_segments(moves: list[PliedMove]) -> tuple:
    if not moves:
        return ()

    groups: list[list[PliedMove]] = []
    current: list[PliedMove] = [moves[0]]
    for move in moves[1:]:
        if move.comment:
            groups.append(current)
            current = [move]
        else:
            current.append(move)
    groups.append(current)

    segments = []
    for group in groups:
        diagram_move = next((m for m in group if m.diagram_board is not None), None)
        segments.append(Segment(
            moves=tuple(group),
            comment=group[0].comment,
            diagram_move=diagram_move,
        ))
    return tuple(segments)


def parse_pgn(pgn_text: str) -> RenderModel:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("PGN contains no game")
    return RenderModel(
        headers=_parse_headers(game),
        segments=_build_segments(_collect_moves(game)),
    )


# ---------------------------------------------------------------------------
# PDF building
# ---------------------------------------------------------------------------

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


def _subtitle_text(headers: GameHeaders) -> str | None:
    date_str = _format_date(headers.date)
    parts = [p for p in [headers.event, date_str] if p]
    return ", ".join(parts) if parts else None


def _title_flowables(headers: GameHeaders, styles: dict) -> list:
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


def _moves_text(segment: Segment) -> str:
    tokens: list[str] = []
    for move in segment.moves:
        ply = move.ply
        move_number = (ply + 1) // 2
        san_with_nag = move.san + (move.nag_symbol or "")
        if ply % 2 == 1:
            tokens.append(f"{move_number}. {san_with_nag}")
        else:
            if not tokens:
                tokens.append(f"{move_number}... {san_with_nag}")
            else:
                tokens.append(san_with_nag)
    return " ".join(tokens)


def _caption_text(move: PliedMove) -> str:
    move_number = (move.ply + 1) // 2
    if move.ply % 2 == 1:
        return f"After {move_number}. {move.san}"
    return f"After {move_number} ... {move.san}"


def _diagram_flowables(
    diagram_move: PliedMove,
    orientation: str,
    styles: dict,
    text_width: float,
) -> list:
    chess_orientation = chess.WHITE if orientation == "white" else chess.BLACK
    svg_text = chess.svg.board(
        diagram_move.diagram_board,
        orientation=chess_orientation,
        size=300,
    )
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
    table = Table([[drawing]], colWidths=[text_width])
    table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))

    caption = Paragraph(_caption_text(diagram_move), styles["Caption"])
    return [Spacer(0, 12), table, caption, Spacer(0, 12)]


def _segment_flowables(
    segment: Segment,
    orientation: str,
    styles: dict,
    text_width: float,
) -> list:
    flowables: list = []
    if segment.diagram_move is not None:
        flowables.extend(_diagram_flowables(segment.diagram_move, orientation, styles, text_width))
    flowables.append(Paragraph(html.escape(_moves_text(segment)), styles["Moves"]))
    if segment.comment:
        flowables.append(Paragraph(html.escape(segment.comment), styles["Comment"]))
    return flowables


def render_pdf(
    pgn_text: str,
    output_path: Path,
    orientation: str = "white",
) -> None:
    model = parse_pgn(pgn_text)
    styles = _build_styles()

    story: list = []
    story.extend(_title_flowables(model.headers, styles))
    for segment in model.segments:
        story.extend(_segment_flowables(segment, orientation, styles, TEXT_WIDTH))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    doc.build(story)
