# annotate.cli.commands.see
import webbrowser

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
        url = session.get_service().upload_to_lichess(game_id=game_id)
    except UseCaseError as exc:
        session.err(str(exc))
        return
    webbrowser.open(url)
    session.print(url)
