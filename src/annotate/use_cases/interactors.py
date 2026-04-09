from dataclasses import replace

from annotate.domain.annotation import Annotation
from annotate.domain.model import derive_segments, total_plies
from annotate.domain.segment import SegmentContent


def split_segment(annotation: Annotation, ply: int, label: str) -> Annotation:
    """Return a new ``Annotation`` with a turning point inserted at ``ply``.

    The segment that previously contained ``ply`` is split at that ply: the
    earlier half retains its existing content, and the new segment starting at
    ``ply`` receives ``label`` as its initial label with empty annotation text.

    Args:
        annotation: The current annotation to split.
        ply:        The 1-based ply at which to insert the new turning point.
                    Must be in the range ``[2, total_plies]``.
        label:      Initial label for the newly created segment.

    Raises:
        ValueError: if ``ply`` is out of range or is already a turning point.
    """
    n = total_plies(annotation.pgn)
    # Ply 1 is already the mandatory first turning point; ply must be at least 2.
    if not (2 <= ply <= n):
        raise ValueError(
            f"Split ply {ply} is out of range; must be between 2 and {n}"
        )
    if ply in annotation.turning_points:
        raise ValueError(f"A segment already starts at ply {ply}")

    # Insert the new turning point and create empty content for the new segment.
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
    """Remove the turning point at ``ply``, absorbing it into the preceding segment.

    The segment's label and annotation text are discarded when the segment is
    removed. If the segment has any authored content (non-blank label or annotation)
    and ``force`` is False, the annotation is returned unchanged and the second
    element of the returned tuple is False — giving the caller an opportunity to
    confirm before data loss occurs. Pass ``force=True`` to discard content without
    a confirmation round-trip.

    Args:
        annotation: The current annotation.
        ply:        The turning-point ply to remove.
        force:      If True, discard authored content without confirmation.

    Returns:
        ``(updated_annotation, merged)`` — ``merged`` is True when the turning
        point was actually removed, False when it was skipped due to content.

    Raises:
        ValueError: if ``ply`` is not a turning point, or if ``ply == 1``
                    (the first segment cannot be merged into anything).
    """
    if ply not in annotation.turning_points:
        raise ValueError(f"No segment starts at ply {ply}")
    if ply == 1:
        raise ValueError("Cannot merge the first segment — nothing precedes it")

    later = annotation.segment_contents[ply]
    has_content = later.has_authored_content()
    # If the segment has authored content and force is False, signal the caller.
    if has_content and not force:
        return annotation, False

    # Remove the turning point and its associated content.
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


def merge_segments_by_index(annotation: Annotation, m: int, n: int) -> Annotation:
    """Collapse segments ``m`` through ``n`` (1-based, inclusive) into a single segment.

    The merged segment occupies the ply range from the start of segment ``m`` to
    the end of segment ``n``. Its label is the space-joined sequence of non-blank
    stripped labels from segments ``m … n``; its annotation is the blank-line-joined
    sequence of non-blank stripped annotation texts from those segments.

    Args:
        annotation: The current annotation.
        m:          1-based index of the first segment to merge (inclusive).
        n:          1-based index of the last segment to merge (inclusive).

    Raises:
        ValueError: if ``m`` or ``n`` are out of range, or if ``m >= n``.
    """
    segments = derive_segments(annotation)
    total = len(segments)
    if not (1 <= m < n <= total):
        raise ValueError(
            f"Segment indices must satisfy 1 <= m < n <= {total}; got m={m}, n={n}"
        )

    # Slice out the segments to be merged (0-based indexing into the list).
    to_merge = segments[m - 1 : n]

    # Concatenate non-blank labels with a space separator.
    merged_label = " ".join(s.label.strip() for s in to_merge if s.label.strip())
    # Concatenate non-blank annotations separated by a blank line.
    merged_annotation = "\n\n".join(
        s.annotation.strip() for s in to_merge if s.annotation.strip()
    )

    # The merged segment keeps the turning point of the first segment in the range.
    first_tp = to_merge[0].turning_point_ply
    # All other turning points in the range are removed.
    remove_tps = {s.turning_point_ply for s in to_merge[1:]}

    new_turning_points = [tp for tp in annotation.turning_points if tp not in remove_tps]
    new_contents = {tp: c for tp, c in annotation.segment_contents.items() if tp not in remove_tps}
    # Replace the first segment's content with the merged result.
    new_contents[first_tp] = replace(
        annotation.segment_contents[first_tp],
        label=merged_label,
        annotation=merged_annotation,
    )

    return replace(
        annotation,
        turning_points=new_turning_points,
        segment_contents=new_contents,
    )
