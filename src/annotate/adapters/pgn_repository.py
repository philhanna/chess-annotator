"""PGN parsing helpers for the annotate application."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import PurePath

import chess
import chess.pgn


NAG_DIAGRAM = 220


@dataclass(frozen=True)
class GameSummary:
    """Summary fields for one game in a PGN collection."""

    index: int
    label: str
    white: str
    black: str
    event: str
    round: str
    date: str
    result: str


@dataclass(frozen=True)
class MoveEntry:
    """Mainline move view model for one ply."""

    ply: int
    side: str
    move_number: int
    san: str
    comment: str
    comment_preview: str
    diagram: bool
    fen: str
    is_initial_position: bool = False


@dataclass(frozen=True)
class ParsedGame:
    """Parsed representation of one PGN game for the annotate UI."""

    summary: GameSummary
    moves: tuple[MoveEntry, ...]
    initial_fen: str
    game: chess.pgn.Game


def parse_pgn_collection(pgn_text: str) -> tuple[ParsedGame, ...]:
    """Parse all games from a PGN string."""

    handle = io.StringIO(pgn_text)
    games: list[ParsedGame] = []

    index = 0
    while True:
        game = chess.pgn.read_game(handle)
        if game is None:
            break

        games.append(
            parse_game(game, index=index)
        )
        index += 1

    return tuple(games)


def parse_game(game: chess.pgn.Game, index: int) -> ParsedGame:
    """Build the parsed annotate representation for one game."""

    return ParsedGame(
        summary=build_game_summary(game, index=index),
        moves=tuple(build_move_entries(game)),
        initial_fen=game.board().fen(),
        game=game,
    )


def build_game_summary(game: chess.pgn.Game, index: int) -> GameSummary:
    """Build a display summary for one game."""

    headers = game.headers
    white = normalize_header(headers.get("White", "?"))
    black = normalize_header(headers.get("Black", "?"))
    event = normalize_header(headers.get("Event", "?"))
    round_name = normalize_header(headers.get("Round", "?"))
    date = normalize_header(headers.get("Date", "?"))
    result = normalize_header(headers.get("Result", "*"))

    parts = [f"{white} vs {black}"]
    detail_parts = [part for part in [event, round_name, date, result] if part]
    if detail_parts:
        parts.append(" | ".join(detail_parts))

    return GameSummary(
        index=index,
        label=" — ".join(parts),
        white=white,
        black=black,
        event=event,
        round=round_name,
        date=date,
        result=result,
    )


def build_move_entries(game: chess.pgn.Game) -> list[MoveEntry]:
    """Build flat move entries for the game's mainline."""

    entries: list[MoveEntry] = [
        MoveEntry(
            ply=0,
            side="white",
            move_number=0,
            san="Start",
            comment=game.comment.strip(),
            comment_preview=truncate_comment(game.comment),
            diagram=False,
            fen=game.board().fen(),
            is_initial_position=True,
        )
    ]
    node = game

    while node.variations:
        node = node.variations[0]
        ply = node.ply()
        entries.append(
            MoveEntry(
                ply=ply,
                side="white" if ply % 2 else "black",
                move_number=(ply + 1) // 2,
                san=node.san(),
                comment=node.comment.strip(),
                comment_preview=truncate_comment(node.comment),
                diagram=NAG_DIAGRAM in node.nags,
                fen=node.board().fen(),
                is_initial_position=False,
            )
        )

    return entries


def normalize_header(value: str) -> str:
    """Normalize placeholder PGN header values to empty strings."""

    return "" if value in {"?", "????.??.??"} else value.strip()


def truncate_comment(comment: str, limit: int = 36) -> str:
    """Return a single-line preview of a PGN comment."""

    squashed = " ".join(comment.split())
    if not squashed:
        return ""
    if len(squashed) <= limit:
        return squashed
    return squashed[: limit - 1].rstrip() + "…"


def selected_node(game: chess.pgn.Game, ply: int) -> chess.pgn.Game | chess.pgn.ChildNode | None:
    """Return the mainline node for the given ply, or ``None`` if absent."""

    if ply == 0:
        return game

    node = game
    while node.variations:
        node = node.variations[0]
        if node.ply() == ply:
            return node
    return None


def serialize_pgn_collection(games: tuple[ParsedGame, ...]) -> str:
    """Serialize the current PGN collection in export form."""

    parts: list[str] = []
    exporter = chess.pgn.StringExporter(
        headers=True,
        variations=True,
        comments=True,
        columns=80,
    )

    for parsed_game in games:
        parts.append(parsed_game.game.accept(exporter).strip())

    if not parts:
        return ""
    return "\n\n".join(parts) + "\n"


def suggested_output_name(source_name: str | None) -> str:
    """Return a suggested output filename for browser save."""

    if not source_name:
        return "annotated-game.pgn"

    source_path = PurePath(source_name)
    stem = source_path.stem or source_path.name or "annotated-game"
    suffix = source_path.suffix or ".pgn"
    return f"{stem}-annotated{suffix}"
