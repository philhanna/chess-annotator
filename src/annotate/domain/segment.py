from dataclasses import dataclass


@dataclass
class SegmentContent:
    """Author-managed content for one segment.

    Instances are keyed by the segment's turning-point ply in
    ``Annotation.segment_contents``. The rendering pipeline and use-case
    layer consume this data through ``SegmentView``, which combines the
    content with the computed ply range.
    """

    label: str = ""
    annotation: str = ""
    show_diagram: bool = True

    @property
    def commentary(self) -> str:
        """Alias for ``annotation``, retained for the rendering pipeline."""
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
    """Legacy flat segment shape retained for adapter compatibility.

    ``SegmentContent`` and ``SegmentView`` are the current domain primitives.
    This class exists only where older code has not yet been migrated and
    should not be used in new code.
    """

    start_ply: int
    label: str = ""
    commentary: str = ""
    show_diagram: bool = True
