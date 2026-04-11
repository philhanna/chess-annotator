from dataclasses import dataclass, field

from annotate.domain.segment import SegmentContent


@dataclass(frozen=True)
class GameId:
    """Strongly-typed, whitespace-normalised identifier for a stored annotated game.

    The raw string is stripped of leading and trailing whitespace in ``__post_init__``,
    so ``GameId("  foo  ")`` and ``GameId("foo")`` are equal. An empty or
    whitespace-only value raises ``ValueError``.
    """

    value: str

    def __post_init__(self) -> None:
        """Normalise and validate the identifier on construction."""
        normalized = self.value.strip()
        if not normalized:
            raise ValueError("game_id must not be empty")
        # Use object.__setattr__ because the dataclass is frozen.
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        """Return the raw identifier string."""
        return self.value


@dataclass(frozen=True)
class TurningPoint:
    """A validated turning-point ply — the 1-based ply at which a new segment begins.

    Raises ``ValueError`` if ``ply`` is less than 1, since ply 0 represents the
    starting position before any move is made and is not a valid segment boundary.
    """

    ply: int

    def __post_init__(self) -> None:
        """Validate that the ply is a legal segment boundary."""
        if self.ply < 1:
            raise ValueError("turning point ply must be >= 1")


@dataclass(frozen=True)
class SessionState:
    """Snapshot of whether a game currently has an open editing session.

    Used by higher-level code that needs to inspect session status without
    going through the repository layer. ``is_open`` is True when a working
    copy exists; ``has_unsaved_changes`` is True when the working copy
    differs from the canonical files.
    """

    game_id: GameId
    is_open: bool = False
    has_unsaved_changes: bool = False


@dataclass
class Annotation:
    """Root aggregate for one annotated chess game.

    Holds the game PGN, display metadata (title, author, date, sides), and the
    full segment structure (turning points + per-segment content). The two
    collections must be kept in sync: ``turning_points`` is a sorted list of
    1-based ply numbers and ``segment_contents`` maps each of those plies to a
    ``SegmentContent`` instance. ``__post_init__`` enforces this invariant and
    normalises both collections on construction.

    The canonical on-disk representation is a pair of files per game:

    * ``annotated.pgn`` — the cleaned PGN with ``{ [%tp] }`` comments at each
      turning-point ply and no other comments or NAGs.
    * ``annotation.json`` — segment labels and annotation text keyed by ply,
      plus top-level game metadata.
    """

    title: str
    author: str
    date: str
    pgn: str
    player_side: str
    game_id: str | None = None
    annotation_id: int | str | None = None
    turning_points: list[int] = field(default_factory=lambda: [1])
    segment_contents: dict[int, SegmentContent] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalise and validate all fields, ensuring turning points and segment contents are in sync."""
        # Resolve game_id, falling back to annotation_id for legacy callers.
        if self.game_id is None:
            if self.annotation_id is None:
                raise ValueError("game_id is required")
            self.game_id = str(self.annotation_id)
        # Run the value through GameId to strip whitespace and validate.
        self.game_id = GameId(str(self.game_id)).value

        # Keep annotation_id in sync for any code that still reads it.
        if self.annotation_id is None:
            self.annotation_id = self.game_id

        # Validate each turning point and produce a sorted, de-duplicated list.
        normalized_points = [TurningPoint(int(p)).ply for p in self.turning_points]
        if not normalized_points:
            normalized_points = [1]
        normalized_points = sorted(normalized_points)
        if normalized_points[0] != 1:
            raise ValueError("the first turning point must be ply 1")
        if len(set(normalized_points)) != len(normalized_points):
            raise ValueError("turning points must be unique")
        self.turning_points = normalized_points

        # Coerce any plain dicts in segment_contents to SegmentContent instances.
        normalized_contents = {
            int(ply): (
                content
                if isinstance(content, SegmentContent)
                else SegmentContent(**content)
            )
            for ply, content in self.segment_contents.items()
        }
        # If no content was provided, seed empty content for each turning point.
        if not normalized_contents:
            normalized_contents = {
                ply: SegmentContent()
                for ply in normalized_points
            }
        # The content keys must exactly match the turning-point set.
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
        game_id: str | None = None,
        annotation_id: int | str | None = None,
    ) -> "Annotation":
        """Build a new annotation with a single initial segment starting at ply 1."""
        return cls(
            title=title,
            author=author,
            date=date,
            pgn=pgn,
            player_side=player_side,
            game_id=game_id,
            annotation_id=annotation_id,
            turning_points=[1],
            segment_contents={1: SegmentContent()},
        )

    def content_at(self, turning_point_ply: int) -> SegmentContent:
        """Return the mutable ``SegmentContent`` for the segment that starts at ``turning_point_ply``.

        Raises ``KeyError`` if ``turning_point_ply`` is not a turning point.
        """
        return self.segment_contents[turning_point_ply]

    @property
    def segments(self):
        """Return derived ``SegmentView`` objects for every turning point, in order.

        Delegates to ``derive_segments`` in the model layer. The import is deferred
        to avoid a circular dependency between the annotation and model modules.
        """
        from annotate.domain.model import derive_segments

        return derive_segments(self)


# Backward-compatible alias.
AnnotatedGame = Annotation
