import json

from annotate.cli import session


def cmd_json(_tokens: list[str]) -> None:
    game_id = session.require_open_session()
    if game_id is None:
        return
    repo = session.get_repo()
    try:
        annotation = repo.load_working_copy(game_id)
    except FileNotFoundError:
        session.err(f"Session is not open for game: {game_id}")
        return
    payload = {
        "game_id": annotation.game_id,
        "title": annotation.title,
        "segments": {
            str(ply): {
                "label": content.label,
                "annotation": content.annotation,
                "show_diagram": content.show_diagram,
            }
            for ply, content in annotation.segment_contents.items()
        },
    }
    session.print(json.dumps(payload, indent=2))
