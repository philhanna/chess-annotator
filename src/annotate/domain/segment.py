from dataclasses import dataclass


@dataclass
class SegmentContent:
    """Store the author-managed content for one segment.

    Segment content is keyed by the segment's turning-point ply in the
    domain model. The rendering and review layers consume this data via
    derived segment views that combine the content with computed move
    ranges.
    """

    label: str = ""
    annotation: str = ""
    show_diagram: bool = True

    @property
    def commentary(self) -> str:
        """Backward-compatible alias for older rendering code."""
        return self.annotation

    @commentary.setter
    def commentary(self, value: str) -> None:
        self.annotation = value

    def has_authored_content(self) -> bool:
        """Return whether the author has entered any meaningful content."""
        return bool(self.label.strip()) or bool(self.annotation.strip())


@dataclass(frozen=True)
class SegmentView:
    """Represent one derived segment spanning a contiguous ply range."""

    turning_point_ply: int
    start_ply: int
    end_ply: int
    content: SegmentContent

    @property
    def label(self) -> str:
        return self.content.label

    @property
    def annotation(self) -> str:
        return self.content.annotation

    @property
    def commentary(self) -> str:
        return self.content.annotation

    @property
    def show_diagram(self) -> bool:
        return self.content.show_diagram


@dataclass
class Segment:
    """Legacy mutable segment shape kept for older adapters.

    Phase 1 introduces ``SegmentContent`` and ``SegmentView`` as the new
    domain primitives, but the repository and CLI still refer to the old
    flat segment structure. Keeping this type during the transition makes
    later phases easier to stage.
    """

    start_ply: int
    label: str = ""
    commentary: str = ""
    show_diagram: bool = True
