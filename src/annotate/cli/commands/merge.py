from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_merge(tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    ply = session.parse_move_side(tokens, "merge <move><w|b>")
    if ply is None:
        return
    try:
        session.get_service().remove_turning_point(game_id=game_id, ply=ply)
        session.print("Segments merged.")
        return
    except UseCaseError as exc:
        if "force is required" not in str(exc):
            session.err(str(exc))
            return
    answer = input("Segment content will be discarded. Merge anyway? (yes/no): ").strip().lower()
    if answer != "yes":
        session.print("Merge cancelled.")
        return
    try:
        session.get_service().remove_turning_point(game_id=game_id, ply=ply, force=True)
    except UseCaseError as exc:
        session.err(str(exc))
        return
    session.print("Segments merged.")
