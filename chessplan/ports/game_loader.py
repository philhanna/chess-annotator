from __future__ import annotations

from pathlib import Path
from typing import Protocol

from chessplan.domain import GameRecord


class GameLoader(Protocol):
    """Port for loading a single chess game from external storage."""

    def load_game(self, pgn_path: Path) -> GameRecord:
        """Load a game from `pgn_path` and return a normalized record."""
        ...
