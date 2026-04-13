import httpx

from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_delete(tokens: list[str]) -> None:
    game_id = tokens[0] if tokens else session.require_open_session()
    if game_id is None:
        session.err("Usage: delete <game-id>")
        return
    answer = input(f"Delete '{game_id}'? (yes/no): ").strip().lower()
    if answer != "yes":
        session.print("Delete cancelled.")
        return
    try:
        response = session.get_client().delete(f"/games/{game_id}")
        session._raise_for_error(response)
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return
    if session.state.game_id == game_id:
        session.state.game_id = None
        session.state.current_turning_point_ply = None
    session.print(f"Deleted: {game_id}")
