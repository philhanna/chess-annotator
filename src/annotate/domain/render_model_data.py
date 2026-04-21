"""Frozen top-level value object for rendered PGN content."""

from __future__ import annotations

from dataclasses import dataclass

from annotate.domain.game_headers import GameHeaders
from annotate.domain.segment import Segment


@dataclass(frozen=True)
class RenderModel:
    """Top-level immutable model consumed by document renderers."""

    headers: GameHeaders
    segments: tuple[Segment, ...]
