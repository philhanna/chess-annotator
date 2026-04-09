from dataclasses import replace

from annotate.domain.annotation import Annotation
from annotate.domain.model import derive_segments, total_plies
from annotate.domain.segment import SegmentContent


def split_segment(annotation: Annotation, ply: int, label: str) -> Annotation:
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


def merge_segments_by_index(annotation: Annotation, m: int, n: int) -> Annotation:
    segments = derive_segments(annotation)
    total = len(segments)
    if not (1 <= m < n <= total):
        raise ValueError(
            f"Segment indices must satisfy 1 <= m < n <= {total}; got m={m}, n={n}"
        )

    to_merge = segments[m - 1 : n]

    merged_label = " ".join(s.label.strip() for s in to_merge if s.label.strip())
    merged_annotation = "\n\n".join(
        s.annotation.strip() for s in to_merge if s.annotation.strip()
    )

    first_tp = to_merge[0].turning_point_ply
    remove_tps = {s.turning_point_ply for s in to_merge[1:]}

    new_turning_points = [tp for tp in annotation.turning_points if tp not in remove_tps]
    new_contents = {tp: c for tp, c in annotation.segment_contents.items() if tp not in remove_tps}
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
