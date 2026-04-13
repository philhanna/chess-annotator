import httpx

from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_save(_tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    try:
        response = session.get_client().post(f"/games/{game_id}/session/save")
        session._raise_for_error(response)
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return
    session.print("Saved.")
