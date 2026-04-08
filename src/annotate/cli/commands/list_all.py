from annotate.cli import session
from annotate.use_cases import SessionNotOpenError


def cmd_list(_tokens: list[str]) -> None:
    summaries = session.get_service().list_games()
    if not summaries:
        session.print("No games found.")
        return
    for game in summaries:
        status = " [in progress]" if game.in_progress else ""
        session.print(
            f"{game.game_id}  {game.white} vs {game.black}  "
            f"{game.event}  {game.date}  {game.result}{status}"
        )


def cmd_list_segments(_tokens: list[str]) -> None:
    try:
        _print_segment_list()
    except SessionNotOpenError as exc:
        session.err(str(exc))


def _print_segment_list() -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    game_state = session.get_service().open_game(game_id)
    unsaved = "  [unsaved changes]" if game_state.has_unsaved_changes else ""
    session.print(f"{game_state.title}  ({game_id}){unsaved}")
    session.print()
    range_width = max(len("Move range"), *(len(s.move_range) for s in game_state.segments))
    session.print(f"  #  {'Move range':<{range_width}}  Label")
    for index, seg in enumerate(game_state.segments, start=1):
        is_current = seg.turning_point_ply == session.state.current_turning_point_ply
        marker = "*" if is_current else " "
        session.print(f"{marker}{index:>2}  {seg.move_range:<{range_width}}  {seg.label or '(blank)'}")
    session.print()
