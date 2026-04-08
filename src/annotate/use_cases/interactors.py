from dataclasses import replace

from annotate.domain.annotation import Annotation
from annotate.domain.model import total_plies
from annotate.domain.segment import SegmentContent


def split_segment(annotation: Annotation, ply: int, label: str) -> Annotation:
    """Split the containing segment by inserting a new turning point."""
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
    """Merge the segment starting at ``ply`` into the preceding segment."""
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
