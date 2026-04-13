from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_split(tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    ply = session.parse_move_side(tokens, "split <move><w|b> [label]")
    if ply is None:
        return
    label = (
        " ".join(tokens[1:]).strip("\"'")
        if len(tokens) > 1
        else session.prompt("Label for new segment", default="")
    )
    try:
        segments = session.get_service().add_turning_point(game_id=game_id, ply=ply, label=label)
    except UseCaseError as exc:
        session.err(str(exc))
        return
    for seg in segments:
        if seg.turning_point_ply == ply:
            session.state.current_turning_point_ply = ply
            break
    session.print("Segment split.")
