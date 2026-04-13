import httpx

from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_label(tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    current = session.current_segment_summary()
    if current is None:
        session.err("No current segment.")
        return
    if not tokens:
        session.err("Usage: label <text>")
        return
    ply = current.turning_point_ply
    try:
        response = session.get_client().patch(
            f"/games/{game_id}/session/segments/{ply}",
            json={"label": " ".join(tokens).strip("\"'")},
        )
        session._raise_for_error(response)
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return
    session.print("Label updated.")
