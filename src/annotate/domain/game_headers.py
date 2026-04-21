"""Frozen value object for the header fields shown in the rendered output."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameHeaders:
    """Normalized header fields used in the rendered document title block."""

    white: str
    black: str
    event: str
    date: str
    opening: str
