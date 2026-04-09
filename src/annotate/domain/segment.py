from dataclasses import dataclass


@dataclass
class SegmentContent:
    """Author-managed content for one annotation segment.

    Stores the three pieces of data a user can edit for a segment: a short label
    that titles the segment in the rendered document, free-form annotation text,
    and a flag that controls whether a board diagram is included. Instances are
    keyed by their turning-point ply in ``Annotation.segment_contents`` and are
    mutated in-place by use-case methods.
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
        """Set ``annotation`` via the legacy ``commentary`` name."""
        self.annotation = value

    def has_authored_content(self) -> bool:
        """Return True when the author has entered any meaningful label or annotation text.

        Both fields are stripped before checking, so a segment that contains only
        whitespace is treated as empty.
        """
        return bool(self.label.strip()) or bool(self.annotation.strip())


@dataclass(frozen=True)
class SegmentView:
    """Immutable derived view of one segment, combining stored content with computed ply bounds.

    Created exclusively by ``derive_segments`` in the model layer; callers should never
    construct instances directly. All ply values are 1-based and inclusive: the segment
    covers every ply in the closed range [start_ply, end_ply].

    ``turning_point_ply`` is the ply at which this segment starts in the game and is
    the key used to look up its ``SegmentContent`` in ``Annotation.segment_contents``.
    For all segments ``start_ply == turning_point_ply``; the field exists separately
    for clarity.
    """

    turning_point_ply: int
    start_ply: int
    end_ply: int
    content: SegmentContent

    @property
    def label(self) -> str:
        """The segment label, delegated to the underlying ``SegmentContent``."""
        return self.content.label

    @property
    def annotation(self) -> str:
        """The annotation text, delegated to the underlying ``SegmentContent``."""
        return self.content.annotation

    @property
    def commentary(self) -> str:
        """Legacy alias for ``annotation``, delegated to the underlying ``SegmentContent``."""
        return self.content.annotation

    @property
    def show_diagram(self) -> bool:
        """Whether a board diagram should be rendered for this segment."""
        return self.content.show_diagram


@dataclass
class Segment:
    """Legacy flat segment shape retained for adapter compatibility.

    ``SegmentContent`` and ``SegmentView`` are the current domain primitives;
    this class exists only in code paths that have not yet been migrated and
    should not be used in new code.
    """

    start_ply: int
    label: str = ""
    commentary: str = ""
    show_diagram: bool = True
