"""PGN parsing helpers for the annotate application."""

from __future__ import annotations

import io
from dataclasses import dataclass

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


@dataclass(frozen=True)
class ParsedGame:
    """Parsed representation of one PGN game for the annotate UI."""

    summary: GameSummary
    moves: tuple[MoveEntry, ...]
    initial_fen: str


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
            ParsedGame(
                summary=build_game_summary(game, index=index),
                moves=tuple(build_move_entries(game)),
                initial_fen=game.board().fen(),
            )
        )
        index += 1

    return tuple(games)


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

    entries: list[MoveEntry] = []
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
