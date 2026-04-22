"""ParsedGame domain model for one annotate-UI game."""

from __future__ import annotations

from dataclasses import dataclass

import chess.pgn

from annotate.domain.game_summary import GameSummary
from annotate.domain.move_entry import MoveEntry


@dataclass(frozen=True)
class ParsedGame:
    """Parsed representation of one PGN game for the annotate UI."""

    summary: GameSummary
    moves: tuple[MoveEntry, ...]
    initial_fen: str
    flipped: bool
    game: chess.pgn.Game
