"""Domain model and PGN parsing helpers for PDF rendering."""

import calendar
import io

import chess
import chess.pgn

from annotate.domain.game_headers import GameHeaders
from annotate.domain.plied_move import PliedMove
from annotate.domain.render_model_data import RenderModel
from annotate.domain.segment import Segment

NAG_SYMBOLS = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}
NAG_DIAGRAM = 220


# ---------------------------------------------------------------------------
# Pure formatting functions
# ---------------------------------------------------------------------------

def format_date(raw: str) -> str:
    """Convert a PGN date tag into a compact human-readable string."""

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


def subtitle_text(headers: GameHeaders) -> str | None:
    """Build the subtitle line from event and date metadata when available."""

    date_str = format_date(headers.date)
    parts = [p for p in [headers.event, date_str] if p]
    return ", ".join(parts) if parts else None


def moves_text(segment: Segment) -> str:
    """Format a segment's moves into display text with move numbers and NAGs."""

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


def caption_text(move: PliedMove) -> str:
    """Return the caption shown below a rendered diagram."""

    move_number = (move.ply + 1) // 2
    if move.ply % 2 == 1:
        return f"After {move_number}. {move.san}"
    return f"After {move_number} ... {move.san}"


# ---------------------------------------------------------------------------
# PGN parsing
# ---------------------------------------------------------------------------

def parse_headers(game: chess.pgn.Game) -> GameHeaders:
    """Extract the subset of PGN headers used by the render model."""

    def tag(name: str) -> str:
        """Return blank strings instead of PGN placeholder values."""

        val = game.headers.get(name, "")
        return "" if val == "?" else val

    return GameHeaders(
        white=tag("White"),
        black=tag("Black"),
        event=tag("Event"),
        date=tag("Date"),
        opening=game.headers.get("Opening", ""),
    )


def collect_moves(game: chess.pgn.Game) -> list[PliedMove]:
    """Read the mainline moves and capture annotations relevant to rendering."""

    moves = []
    node = game
    while node.variations:
        node = node.variations[0]
        nag_symbol = next((NAG_SYMBOLS[n] for n in node.nags if n in NAG_SYMBOLS), None)
        has_diagram = NAG_DIAGRAM in node.nags
        # Copy the board only for requested diagrams so later traversal cannot mutate it.
        diagram_board = node.board().copy() if has_diagram else None
        moves.append(PliedMove(
            ply=node.ply(),
            san=node.san(),
            nag_symbol=nag_symbol,
            diagram_board=diagram_board,
            comment=node.comment.strip(),
        ))
    return moves


def build_segments(moves: list[PliedMove]) -> tuple:
    """Split moves into render segments anchored by leading comments."""

    if not moves:
        return ()

    groups: list[list[PliedMove]] = []
    current: list[PliedMove] = [moves[0]]
    for move in moves[1:]:
        # A comment starts a new prose segment and belongs to the move it annotates.
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
    """Parse PGN text into the immutable render model used by adapters."""

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("PGN contains no game")
    return RenderModel(
        headers=parse_headers(game),
        segments=build_segments(collect_moves(game)),
    )
