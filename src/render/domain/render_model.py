"""Domain model and PGN parsing helpers for PDF rendering.

This module is the heart of the domain layer.  It owns three concerns:

1. **Pure formatting** — functions that turn domain objects into display
   strings (move numbers, captions, subtitles) without any I/O or rendering
   library dependencies.

2. **PGN parsing** — functions that read a ``chess.pgn.Game`` and produce the
   immutable :class:`~render.domain.render_model_data.RenderModel` consumed
   by adapters.

3. **Top-level entry point** — :func:`parse_pgn`, which accepts raw PGN text
   and returns a fully-built :class:`~render.domain.render_model_data.RenderModel`.

NAG handling
------------
PGN Numeric Annotation Glyphs (NAGs) are integer codes attached to moves.
This module recognises NAGs 1–6 (the standard move-quality symbols) and maps
them to the conventional typographic symbols.  NAG 220 is treated as a
diagram request: the board position after that move is captured and stored in
the resulting :class:`~render.domain.plied_move.PliedMove`.
"""

import calendar
import io

import chess
import chess.pgn

from render.domain.game_headers import GameHeaders
from render.domain.plied_move import PliedMove
from render.domain.render_model_data import RenderModel
from render.domain.segment import Segment

NAG_SYMBOLS = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}
NAG_DIAGRAM = 220


# ---------------------------------------------------------------------------
# Pure formatting functions
# ---------------------------------------------------------------------------

def format_date(raw: str) -> str:
    """Convert a PGN date tag into a compact human-readable string.

    PGN dates use the format ``YYYY.MM.DD`` with ``?`` for unknown components.
    This function converts known components into an abbreviated display form:

    * Full date → ``"05 Apr 2024"``
    * Year + month → ``"Apr 2024"``
    * Year only → ``"2024"``
    * Unknown year (or malformed input) → ``""``

    Args:
        raw: A PGN date string such as ``"2024.04.05"`` or ``"2024.??.??"``.

    Returns:
        A human-readable date string, or an empty string when the date cannot
        be meaningfully represented.
    """

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
    """Build the subtitle line from event and date metadata when available.

    Combines the event name and the formatted date into a comma-separated
    string.  Either component may be absent; if both are absent the function
    returns ``None`` so the caller can skip rendering the subtitle entirely.

    Args:
        headers: Normalised game headers produced by :func:`parse_headers`.

    Returns:
        A subtitle string such as ``"London Chess Classic, 05 Apr 2024"``, a
        partial string when only one component is available, or ``None`` when
        neither event nor date can be determined.
    """

    date_str = format_date(headers.date)
    parts = [p for p in [headers.event, date_str] if p]
    return ", ".join(parts) if parts else None


def moves_text(segment: Segment) -> str:
    """Format a segment's moves into a display string with move numbers and NAG symbols.

    Produces the conventional chess notation run used in game annotations, for
    example ``"14. Nf3! Nc6 15. Bb5"`` or ``"14... Nc6 15. Bb5"``.  Rules:

    * White's moves (odd plies) are always prefixed with their move number and a
      period: ``"14. Nf3"``.
    * Black's first move in a segment that starts mid-game gets an ellipsis
      prefix: ``"14... Nc6"``.  Subsequent Black moves within the same token
      run appear bare, i.e. without a number.
    * NAG symbols are appended directly to the SAN with no space: ``"Nf3!"``.
    * The game result string (``"1-0"``, ``"0-1"``, ``"1/2-1/2"``) is appended
      to the last move of the final segment, separated by a space.

    Args:
        segment: The segment whose moves to format.

    Returns:
        A space-joined string of annotated move tokens suitable for display.
    """

    tokens: list[str] = []
    for index, move in enumerate(segment.moves):
        ply = move.ply
        move_number = (ply + 1) // 2
        san_with_nag = move.san + (move.nag_symbol or "")
        if index == len(segment.moves) - 1 and move.result:
            san_with_nag = f"{san_with_nag} {move.result}"
        if ply % 2 == 1:
            tokens.append(f"{move_number}. {san_with_nag}")
        else:
            if not tokens:
                tokens.append(f"{move_number}... {san_with_nag}")
            else:
                tokens.append(san_with_nag)
    return " ".join(tokens)


def caption_text(move: PliedMove) -> str:
    """Return the caption string shown below a rendered board diagram.

    Produces a string of the form ``"After 14. Nf3"`` for White's moves or
    ``"After 14 ... Nc6"`` for Black's moves.  Note the spaces around the
    ellipsis in Black's caption, which is the standard annotation style.

    Args:
        move: The move for which a diagram is being rendered.  Only
            ``move.ply`` and ``move.san`` are used; NAG symbols and comments
            are intentionally excluded from captions.

    Returns:
        A caption string ready for display beneath the diagram.
    """

    move_number = (move.ply + 1) // 2
    if move.ply % 2 == 1:
        return f"After {move_number}. {move.san}"
    return f"After {move_number} ... {move.san}"


# ---------------------------------------------------------------------------
# PGN parsing
# ---------------------------------------------------------------------------

def parse_headers(game: chess.pgn.Game) -> GameHeaders:
    """Extract and normalise the PGN header fields used by the render model.

    Reads the Seven Tag Roster fields relevant to the title block and converts
    PGN placeholder values (``"?"``) to empty strings.  The ``Date`` tag is
    left in raw PGN format (``"YYYY.MM.DD"``) for downstream formatting by
    :func:`format_date`.

    Args:
        game: A parsed PGN game object as returned by ``chess.pgn.read_game``.

    Returns:
        A :class:`~render.domain.game_headers.GameHeaders` instance with
        normalised string values.
    """

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
    """Walk the mainline and return a :class:`PliedMove` for every half-move.

    Only the main variation is traversed; alternative lines are ignored.  For
    each node the function captures the SAN, ply number, any recognised NAG
    symbol, a board snapshot when NAG 220 is present, and the stripped comment.
    The game result is attached to the last move so renderers can append it
    inline without a separate lookup.

    Args:
        game: A parsed PGN game object as returned by ``chess.pgn.read_game``.

    Returns:
        An ordered list of :class:`~render.domain.plied_move.PliedMove`
        instances covering every mainline half-move, or an empty list for a
        game with no moves.
    """

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
    result = game.headers.get("Result", "")
    if moves and result and result != "*":
        final_move = moves[-1]
        moves[-1] = PliedMove(
            ply=final_move.ply,
            san=final_move.san,
            nag_symbol=final_move.nag_symbol,
            diagram_board=final_move.diagram_board,
            comment=final_move.comment,
            result=result,
        )
    return moves


def build_segments(moves: list[PliedMove]) -> tuple:
    """Split a flat move list into commentary segments anchored by comments.

    A new segment is started whenever a move carries a non-empty comment; that
    move becomes the first element of the new segment and its comment becomes
    the segment's prose block.  Moves without comments are appended to the
    current segment.  The first move always opens the first segment regardless
    of whether it has a comment.

    Each segment is also inspected for a diagram move: the first move in the
    segment that carries NAG 220 (i.e. has a non-``None`` ``diagram_board``)
    is stored as ``Segment.diagram_move``.

    Args:
        moves: The ordered flat list of half-moves produced by
            :func:`collect_moves`.

    Returns:
        An immutable tuple of :class:`~render.domain.segment.Segment`
        instances in game order, or an empty tuple when ``moves`` is empty.
    """

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
    """Parse a PGN string into the immutable render model consumed by adapters.

    This is the primary entry point for the domain layer.  It delegates to
    :func:`parse_headers`, :func:`collect_moves`, and :func:`build_segments`
    in sequence and wraps the results in a :class:`RenderModel`.

    Args:
        pgn_text: The full text of a PGN file.  Only the first game is parsed;
            any subsequent games are ignored.

    Returns:
        A fully-populated :class:`~render.domain.render_model_data.RenderModel`
        ready to pass to a document renderer.

    Raises:
        ValueError: If ``pgn_text`` contains no parseable game.
    """

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("PGN contains no game")
    return RenderModel(
        headers=parse_headers(game),
        segments=build_segments(collect_moves(game)),
        pre_game_comment=game.comment.strip(),
    )
