from dataclasses import replace

from annotate.domain.annotation import Annotation
from annotate.domain.model import total_plies
from annotate.domain.segment import SegmentContent


def split_segment(annotation: Annotation, ply: int, label: str) -> Annotation:
    """Return a new Annotation with a turning point inserted at ``ply``.

    The segment that previously contained ``ply`` is split: its existing
    content remains associated with the earlier half and the new segment
    receives ``label`` as its initial label with empty annotation text.

    Raises:
        ValueError: if ``ply`` is out of the range ``[2, total_plies]``, or
            if a turning point already exists at ``ply``.
    """
    n = total_plies(annotation.pgn)
    if not (2 <= ply <= n):
        raise ValueError(
            f"Split ply {ply} is out of range; must be between 2 and {n}"
        )
    if ply in annotation.turning_points:
        raise ValueError(f"A segment already starts at ply {ply}")

    new_turning_points = sorted([*annotation.turning_points, ply])
    new_contents = dict(annotation.segment_contents)
    new_contents[ply] = SegmentContent(label=label)
    return replace(
        annotation,
        turning_points=new_turning_points,
        segment_contents=new_contents,
    )


def merge_segment(
    annotation: Annotation, ply: int, force: bool = False
) -> tuple[Annotation, bool]:
    """Return ``(updated_annotation, merged)`` after removing the turning point at ``ply``.

    The segment at ``ply`` is absorbed into the preceding segment and its
    content is discarded. If the segment has any authored content (label or
    annotation) and ``force`` is False, the original annotation is returned
    unchanged and ``merged`` is False. Pass ``force=True`` to discard content
    without confirmation.

    Raises:
        ValueError: if ``ply`` is not a turning point, or if ``ply == 1``
            (the first turning point cannot be removed).
    """
    if ply not in annotation.turning_points:
        raise ValueError(f"No segment starts at ply {ply}")
    if ply == 1:
        raise ValueError("Cannot merge the first segment — nothing precedes it")

    later = annotation.segment_contents[ply]
    has_content = later.has_authored_content()
    if has_content and not force:
        return annotation, False

    new_turning_points = [tp for tp in annotation.turning_points if tp != ply]
    new_contents = dict(annotation.segment_contents)
    del new_contents[ply]
    return (
        replace(
            annotation,
            turning_points=new_turning_points,
            segment_contents=new_contents,
        ),
        True,
    )
