import httpx

from annotate.cli import session
from annotate.config import get_config
from annotate.use_cases import UseCaseError


def cmd_render(tokens: list[str]) -> None:
    if session.state.open:
        game_id = session.require_open_session()
    elif tokens:
        game_id = tokens[0]
    else:
        session.err("Usage: render <game-id>")
        return
    if game_id is None:
        return

    try:
        response = session.get_client().post(f"/games/{game_id}/render")
        session._raise_for_error(response)
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return

    config = get_config()
    output_path = config.store_dir / game_id / "output.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    session.print(f"Rendered: {output_path}")
