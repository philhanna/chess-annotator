import httpx

from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_merge(tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    if len(tokens) < 2:
        session.err("Usage: merge <m> <n>")
        return
    try:
        m = int(tokens[0])
        n = int(tokens[1])
    except ValueError:
        session.err("Usage: merge <m> <n>")
        return
    if m < 1 or n < 1:
        session.err("Usage: merge <m> <n>")
        return
    try:
        response = session.get_client().post(
            f"/games/{game_id}/session/segments/merge",
            json={"m": m, "n": n},
        )
        session._raise_for_error(response)
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return
    session.print("Segments merged.")
