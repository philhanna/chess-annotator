"""Frozen value object for the header fields shown in the rendered output.

Header values are normalised during PGN parsing: PGN placeholder values such
as ``"?"`` are converted to empty strings so that renderers can use a simple
truthiness check to decide whether to display a field.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameHeaders:
    """Normalised header fields used in the rendered document title block.

    All fields are strings.  An empty string means the value was absent or
    unknown in the source PGN — renderers should omit those fields rather than
    printing a blank or a placeholder.

    Attributes:
        white: Name of the player with the White pieces.
        black: Name of the player with the Black pieces.
        event: Tournament or match name.
        date: Game date in ``YYYY.MM.DD`` PGN format; partial dates use ``?``
            for unknown components (e.g. ``"2024.??.??"``) and are formatted
            for display by :func:`~annotate.domain.render_model.format_date`.
        opening: ECO opening name, if present in the PGN.
    """

    white: str
    black: str
    event: str
    date: str
    opening: str
