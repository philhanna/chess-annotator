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
        session.get_service().merge_segments(game_id=game_id, m=m, n=n)
    except UseCaseError as exc:
        session.err(str(exc))
        return
    session.print("Segments merged.")
