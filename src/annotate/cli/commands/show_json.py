import json

import httpx

from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_json(_tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return

    try:
        # Get game state for the title.
        gs_response = session.get_client().get(f"/games/{game_id}/session")
        session._raise_for_error(gs_response)
        game_state = gs_response.json()

        # Get segment list for plies.
        seg_response = session.get_client().get(f"/games/{game_id}/session/segments")
        session._raise_for_error(seg_response)
        summaries = seg_response.json()
    except (UseCaseError, httpx.TransportError) as exc:
        session.err(str(exc))
        return

    # Fetch full detail for each segment to get the annotation text.
    segments_detail: dict[str, dict] = {}
    for summary in summaries:
        ply = summary["turning_point_ply"]
        try:
            det_response = session.get_client().get(
                f"/games/{game_id}/session/segments/{ply}"
            )
            session._raise_for_error(det_response)
            det = det_response.json()
            segments_detail[str(ply)] = {
                "label": det["label"],
                "annotation": det["annotation"],
            }
        except (UseCaseError, httpx.TransportError) as exc:
            session.err(str(exc))
            return

    payload = {
        "game_id": game_id,
        "title": game_state["title"],
        "segments": segments_detail,
    }
    session.print(json.dumps(payload, indent=2))
