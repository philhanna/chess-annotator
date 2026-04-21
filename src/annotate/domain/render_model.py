# annotate.domain.render_model
import calendar
import io
from dataclasses import dataclass

import chess
import chess.pgn

NAG_SYMBOLS = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}
NAG_DIAGRAM = 220


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
# Pure formatting functions
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


def _subtitle_text(headers: GameHeaders) -> str | None:
    date_str = _format_date(headers.date)
    parts = [p for p in [headers.event, date_str] if p]
    return ", ".join(parts) if parts else None


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


# ---------------------------------------------------------------------------
# PGN parsing
# ---------------------------------------------------------------------------

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
