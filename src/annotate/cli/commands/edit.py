from annotate.adapters.system_editor_launcher import SystemEditorLauncher
from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_edit(_tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    current = session.current_segment_summary()
    if current is None:
        session.err("No current segment.")
        return
    detail = session.get_service().view_segment(
        game_id=game_id,
        turning_point_ply=current.turning_point_ply,
    )
    launcher = SystemEditorLauncher()
    updated = launcher.edit(detail.annotation)
    try:
        session.get_service().set_segment_annotation(
            game_id=game_id,
            turning_point_ply=current.turning_point_ply,
            annotation_text=updated,
        )
    except UseCaseError as exc:
        session.err(str(exc))
        return
    session.print("Annotation updated.")
