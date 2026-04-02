# annotate.use_cases.interactors
from dataclasses import replace

from annotate.domain.annotation import Annotation
from annotate.domain.model import find_segment_index, total_plies
from annotate.domain.segment import Segment


def split_segment(annotation: Annotation, ply: int) -> Annotation:
    """Split the segment containing ``ply`` into two segments.

    The earlier half retains the original segment's ``label`` and
    ``commentary``; its ``show_diagram`` is reset to ``False``. The
    later half starts at ``ply`` with all fields empty.

    Raises ``ValueError`` when:

    - ``ply`` is outside the range ``[2, total_plies]``
    - ``ply`` is already the ``start_ply`` of an existing segment
    """
    n = total_plies(annotation.pgn)
    if not (2 <= ply <= n):
        raise ValueError(
            f"Split ply {ply} is out of range; must be between 2 and {n}"
        )
    for seg in annotation.segments:
        if seg.start_ply == ply:
            raise ValueError(f"A segment already starts at ply {ply}")

    idx = find_segment_index(annotation, ply)
    earlier = replace(annotation.segments[idx], show_diagram=False)
    later = Segment(start_ply=ply)

    new_segments = (
        list(annotation.segments[:idx])
        + [earlier, later]
        + list(annotation.segments[idx + 1:])
    )
    return replace(annotation, segments=new_segments)


def merge_segment(
    annotation: Annotation, ply: int, force: bool = False
) -> tuple[Annotation, bool]:
    """Merge the segment starting at ``ply`` into the preceding segment.

    The earlier segment's content is always retained. The later
    segment's content is discarded.

    Returns ``(new_annotation, True)`` when the merge was performed, or
    ``(annotation, False)`` when the later segment has non-empty content
    and ``force`` is ``False``.

    Raises ``ValueError`` when:

    - no segment starts at ``ply``
    - ``ply`` is the ``start_ply`` of the first segment (nothing precedes it)
    """
    segments = annotation.segments
    idx = next(
        (i for i, s in enumerate(segments) if s.start_ply == ply), None
    )
    if idx is None:
        raise ValueError(f"No segment starts at ply {ply}")
    if idx == 0:
        raise ValueError("Cannot merge the first segment — nothing precedes it")

    later = segments[idx]
    has_content = (
        bool(later.label)
        or bool(later.commentary.strip())
        or later.show_diagram
    )
    if has_content and not force:
        return annotation, False

    new_segments = list(segments[:idx]) + list(segments[idx + 1:])
    return replace(annotation, segments=new_segments), True
