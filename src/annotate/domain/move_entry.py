"""MoveEntry domain model for one ply in a game's mainline."""

from __future__ import annotations

from dataclasses import dataclass


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
