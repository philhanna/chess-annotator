"""GameSummary domain model for one game in a PGN collection."""

from __future__ import annotations

from dataclasses import dataclass


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
    board_title: str
    result: str
