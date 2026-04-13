import httpx

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
        response = session.get_client().post(
            f"/games/{game_id}/session/segments",
            json={"ply": ply, "label": label},
        )
        session._raise_for_error(response)
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return
    segments = response.json()
    for seg in segments:
        if seg["turning_point_ply"] == ply:
            session.state.current_turning_point_ply = ply
            break
    session.print("Segment split.")
