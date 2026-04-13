import httpx

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
    ply = current.turning_point_ply

    try:
        response = session.get_client().get(f"/games/{game_id}/session/segments/{ply}")
        session._raise_for_error(response)
        detail = response.json()
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return

    launcher = SystemEditorLauncher()
    updated = launcher.edit(detail["annotation"])

    try:
        response = session.get_client().patch(
            f"/games/{game_id}/session/segments/{ply}",
            json={"annotation": updated},
        )
        session._raise_for_error(response)
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return
    session.print("Annotation updated.")
