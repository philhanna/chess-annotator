from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_save(_tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    try:
        session.get_service().save_session(game_id)
    except UseCaseError as exc:
        session.err(str(exc))
        return
    session.print("Saved.")
