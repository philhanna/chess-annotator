# annotate.cli.commands.label
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
    try:
        session.get_service().set_segment_label(
            game_id=game_id,
            turning_point_ply=current.turning_point_ply,
            label=" ".join(tokens).strip("\"'"),
        )
    except UseCaseError as exc:
        session.err(str(exc))
        return
    session.print("Label updated.")
