from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MovePair:
    """Represents the SAN moves played in a single full move number.

    Each instance stores the move number together with the optional white
    and black SAN strings for that turn. The black move may be absent when
    a game ends after White's move.
    """

    move_number: int
    white_san: str | None
    black_san: str | None


@dataclass(frozen=True, slots=True)
class GameHeaders:
    """Stores the PGN header fields used by the review workflow.

    The fields default to empty strings so adapters can build a record even
    when a PGN omits optional metadata.
    """

    event: str = ""
    site: str = ""
    date: str = ""
    white: str = ""
    black: str = ""
    result: str = ""
    white_elo: str = ""
    black_elo: str = ""
    termination: str = ""


@dataclass(frozen=True, slots=True)
class GameRecord:
    """Holds the immutable game data needed for review and annotation.

    A record combines normalized PGN header information with a move list
    arranged as full-move pairs for display and validation.
    """

    headers: GameHeaders
    move_pairs: list[MovePair]

    @property
    def max_fullmove_number(self) -> int:
        """Return the highest full-move number present in the game.

        Returns `0` when the game has no recorded moves.
        """

        return self.move_pairs[-1].move_number if self.move_pairs else 0
