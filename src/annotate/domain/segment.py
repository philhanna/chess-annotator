"""Frozen value object describing one rendered commentary segment."""

from __future__ import annotations

from dataclasses import dataclass

from annotate.domain.plied_move import PliedMove


@dataclass(frozen=True)
class Segment:
    """Groups contiguous moves with the comment that introduces that segment."""

    moves: tuple[PliedMove, ...]
    comment: str
    diagram_move: PliedMove | None
