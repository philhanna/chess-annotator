import webbrowser

import httpx

from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_see(tokens: list[str]) -> None:
    if session.state.open:
        game_id = session.require_open_session()
    elif tokens:
        game_id = tokens[0]
    else:
        session.err("Usage: see <game-id>")
        return
    if game_id is None:
        return

    try:
        response = session.get_client().post(f"/games/{game_id}/lichess")
        session._raise_for_error(response)
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return

    url = response.json()["url"]
    webbrowser.open(url)
    session.print(url)
