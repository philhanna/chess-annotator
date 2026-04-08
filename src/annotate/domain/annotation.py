from dataclasses import dataclass, field

from annotate.domain.segment import SegmentContent


@dataclass(frozen=True)
class GameId:
    """Strongly typed identifier for a stored annotated game."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise ValueError("game_id must not be empty")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TurningPoint:
    """Represent the starting ply of a segment."""

    ply: int

    def __post_init__(self) -> None:
        if self.ply < 1:
            raise ValueError("turning point ply must be >= 1")


@dataclass(frozen=True)
class SessionState:
    """Capture whether a game currently has an open editing session."""

    game_id: GameId
    is_open: bool = False
    has_unsaved_changes: bool = False


@dataclass
class Annotation:
    """Aggregate the domain state for one annotated chess game.

    The design's primary source of truth is:

    - ordered turning points stored in the annotated PGN
    - segment content keyed by turning-point ply stored in JSON

    This class models that pairing directly so later persistence work can
    map to it without reshaping the domain again.
    """

    title: str
    author: str
    date: str
    pgn: str
    player_side: str
    diagram_orientation: str
    game_id: str | None = None
    annotation_id: int | str | None = None
    turning_points: list[int] = field(default_factory=lambda: [1])
    segment_contents: dict[int, SegmentContent] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.game_id is None:
            if self.annotation_id is None:
                raise ValueError("game_id is required")
            self.game_id = str(self.annotation_id)
        self.game_id = GameId(str(self.game_id)).value

        if self.annotation_id is None:
            self.annotation_id = self.game_id

        normalized_points = [TurningPoint(int(p)).ply for p in self.turning_points]
        if not normalized_points:
            normalized_points = [1]
        normalized_points = sorted(normalized_points)
        if normalized_points[0] != 1:
            raise ValueError("the first turning point must be ply 1")
        if len(set(normalized_points)) != len(normalized_points):
            raise ValueError("turning points must be unique")
        self.turning_points = normalized_points

        normalized_contents = {
            int(ply): (
                content
                if isinstance(content, SegmentContent)
                else SegmentContent(**content)
            )
            for ply, content in self.segment_contents.items()
        }
        if not normalized_contents:
            normalized_contents = {
                ply: SegmentContent()
                for ply in normalized_points
            }
        if set(normalized_contents) != set(normalized_points):
            raise ValueError(
                "segment content keys must match the turning points exactly"
            )
        self.segment_contents = normalized_contents

    @classmethod
    def create(
        cls,
        title: str,
        author: str,
        date: str,
        pgn: str,
        player_side: str,
        diagram_orientation: str | None = None,
        game_id: str | None = None,
        annotation_id: int | str | None = None,
    ) -> "Annotation":
        """Build a new annotation with a single initial segment at ply 1."""
        if diagram_orientation is None:
            diagram_orientation = "black" if player_side == "black" else "white"
        return cls(
            title=title,
            author=author,
            date=date,
            pgn=pgn,
            player_side=player_side,
            diagram_orientation=diagram_orientation,
            game_id=game_id,
            annotation_id=annotation_id,
            turning_points=[1],
            segment_contents={1: SegmentContent()},
        )

    def content_at(self, turning_point_ply: int) -> SegmentContent:
        """Return the segment content for one turning point."""
        return self.segment_contents[turning_point_ply]

    @property
    def segments(self):
        """Expose derived segment views for compatibility with older code."""
        from annotate.domain.model import derive_segments

        return derive_segments(self)


AnnotatedGame = Annotation
