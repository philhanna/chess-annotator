# annotate.cli.commands.diagram
from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_diagram(tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    current = session.current_segment_summary()
    if current is None:
        session.err("No current segment.")
        return
    desired = None
    if tokens:
        if tokens[0].lower() not in ("on", "off"):
            session.err("Usage: diagram [on|off]")
            return
        desired = tokens[0].lower() == "on"
    try:
        detail = session.get_service().view_segment(
            game_id=game_id,
            turning_point_ply=current.turning_point_ply,
        )
        if desired is None or detail.show_diagram != desired:
            updated = session.get_service().toggle_segment_diagram(
                game_id=game_id,
                turning_point_ply=current.turning_point_ply,
            )
        else:
            updated = detail
    except UseCaseError as exc:
        session.err(str(exc))
        return
    session.print(f"Diagram {'enabled' if updated.show_diagram else 'disabled'}.")
