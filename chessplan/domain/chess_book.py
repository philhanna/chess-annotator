from __future__ import annotations

from dataclasses import dataclass

from chessplan.domain.game import GameHeaders


ALLOWED_CHP_KINDS = frozenset({"plan", "transition", "defense"})


@dataclass(frozen=True, slots=True)
class ChpMarker:
    """Structured data extracted from one ``#chp`` PGN comment."""

    label: str
    kind: str
    comments: str = ""

    def validate(self) -> list[str]:
        """Return validation errors for the parsed marker fields."""

        errors: list[str] = []
        if not self.label.strip():
            errors.append("label is required")
        if not self.kind.strip():
            errors.append("kind is required")
        elif self.kind not in ALLOWED_CHP_KINDS:
            allowed = ", ".join(sorted(ALLOWED_CHP_KINDS))
            errors.append(f"kind must be one of: {allowed}")
        return errors


@dataclass(frozen=True, slots=True)
class PlayedMove:
    """A single played move annotated with enough data for chunk rendering."""

    ply_index: int
    move_number: int
    side: str
    san: str
    uci: str


@dataclass(frozen=True, slots=True)
class BookChunk:
    """One rendered chunk in the generated HTML chess book."""

    label: str | None
    move_text: str
    comments: str
    svg: str | None


@dataclass(frozen=True, slots=True)
class ParsedChessBook:
    """Normalized PGN data needed to render the chess book output."""

    headers: GameHeaders
    moves: list[PlayedMove]
    chunk_markers: dict[int, ChpMarker]
    trailing_comments: str
