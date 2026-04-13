import httpx

from annotate.cli import session
from annotate.use_cases import SegmentSummary, UseCaseError


def cmd_list(_tokens: list[str]) -> None:
    try:
        response = session.get_client().get("/games")
        session._raise_for_error(response)
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return

    summaries = response.json()
    if not summaries:
        session.print("No games found.")
        return
    for game in summaries:
        status = " [in progress]" if game["in_progress"] else ""
        session.print(
            f"{game['game_id']}  {game['white']} vs {game['black']}  "
            f"{game['event']}  {game['date']}  {game['result']}{status}"
        )


def cmd_list_segments(_tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    try:
        response = session.get_client().get(f"/games/{game_id}/session")
        session._raise_for_error(response)
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return

    game_state = response.json()
    unsaved = "  [unsaved changes]" if game_state["has_unsaved_changes"] else ""
    session.print(f"{game_state['title']}  ({game_id}){unsaved}")
    session.print()
    segments = [SegmentSummary(**s) for s in game_state.get("segments", [])]
    range_width = max(len("Move range"), *(len(s.move_range) for s in segments)) if segments else len("Move range")
    session.print(f"  #  {'Move range':<{range_width}}  Label")
    for index, seg in enumerate(segments, start=1):
        is_current = seg.turning_point_ply == session.state.current_turning_point_ply
        marker = "*" if is_current else " "
        session.print(f"{marker}{index:>2}  {seg.move_range:<{range_width}}  {seg.label or '(blank)'}")
    session.print()
