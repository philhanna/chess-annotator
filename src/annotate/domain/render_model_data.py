"""Frozen top-level value object for a fully-parsed PGN game ready for rendering.

:class:`RenderModel` is the contract between the domain parsing layer and all
document renderer adapters.  It contains everything a renderer needs and nothing
it does not: raw PGN structures (``chess.pgn.Game``, move nodes, etc.) do not
appear here.
"""

from __future__ import annotations

from dataclasses import dataclass

from annotate.domain.game_headers import GameHeaders
from annotate.domain.segment import Segment


@dataclass(frozen=True)
class RenderModel:
    """Top-level immutable model consumed by all document renderer adapters.

    Produced by :func:`~annotate.domain.render_model.parse_pgn` and passed
    directly to :class:`~annotate.ports.document_renderer.DocumentRenderer`
    implementations.  Being frozen and composed entirely of frozen value
    objects, instances are safe to pass across threads without copying.

    Attributes:
        headers: Normalised game metadata (players, event, date, opening).
        segments: Ordered tuple of commentary segments covering all mainline
            moves.  The sequence is non-empty for any game that contains at
            least one move.
    """

    headers: GameHeaders
    segments: tuple[Segment, ...]
