from annotate.cli import session
from annotate.use_cases import SegmentNotFoundError, SessionNotOpenError, UseCaseError


def cmd_view(_tokens: list[str]) -> None:
    current = session.current_segment_summary()
    if current is None:
        session.err("No current segment.")
        return
    game_id = session.require_open_session()
    if game_id is None:
        return
    segments = session.current_segments()
    index = next(
        (i for i, s in enumerate(segments, 1) if s.turning_point_ply == current.turning_point_ply),
        None,
    )
    try:
        detail = session.get_service().view_segment(
            game_id=game_id,
            turning_point_ply=current.turning_point_ply,
        )
    except (SessionNotOpenError, SegmentNotFoundError, UseCaseError) as exc:
        session.err(str(exc))
        return

    session.state.current_turning_point_ply = detail.turning_point_ply
    session.print(f"Segment {index}  {detail.move_range}")
    session.print(f"Label: {detail.label or '(blank)'}")
    session.print(f"Moves: {detail.move_list}")
    session.print()
    session.print(detail.annotation or "(no annotation)")
