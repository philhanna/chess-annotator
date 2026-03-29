from __future__ import annotations

from pathlib import Path
from typing import Protocol

from chessplan.domain import GameRecord


class GameLoader(Protocol):
    def load_game(self, pgn_path: Path) -> GameRecord: ...
