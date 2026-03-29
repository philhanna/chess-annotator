from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MovePair:
    move_number: int
    white_san: str | None
    black_san: str | None


@dataclass(frozen=True, slots=True)
class GameHeaders:
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
    headers: GameHeaders
    move_pairs: list[MovePair]

    @property
    def max_fullmove_number(self) -> int:
        return self.move_pairs[-1].move_number if self.move_pairs else 0
