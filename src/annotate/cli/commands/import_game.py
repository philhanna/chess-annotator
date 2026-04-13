from pathlib import Path

import httpx

from annotate.adapters.python_chess_pgn_parser import PythonChessPGNParser
from annotate.cli import strip_comments
from annotate.cli import session
from annotate.config import get_config
from annotate.use_cases import UseCaseError


def cmd_import(tokens: list[str]) -> None:
    if tokens:
        pgn_path = Path(tokens[0]).expanduser()
        if not pgn_path.exists():
            session.err(f"File not found: {pgn_path}")
            return
    else:
        while True:
            pgn_path = Path(session.prompt(".pgn file")).expanduser()
            if pgn_path.exists():
                break
            session.err(f"File not found: {pgn_path}")

    raw_pgn = pgn_path.read_text()
    cleaned_pgn = strip_comments(raw_pgn)
    parser = PythonChessPGNParser()
    try:
        info = parser.parse(cleaned_pgn)
    except ValueError as exc:
        session.err(str(exc))
        return

    total_moves = (info["total_plies"] + 1) // 2
    session.print(
        f"PGN loaded: {info['total_plies']} plies ({total_moves} moves), "
        f"White: {info['white']}, Black: {info['black']}"
    )
    session.print()

    game_id = session.prompt("Game id")
    pgn_date = info["date"].replace("?", "").strip(".") or ""
    date = session.prompt("Date", default=pgn_date)
    while True:
        side = session.prompt("You played (white/black)").lower()
        if side in ("white", "black"):
            break
        session.print("Please enter white or black.")

    config = get_config()
    payload = {
        "game_id": game_id,
        "pgn_text": raw_pgn,
        "player_side": side,
        "author": config.author or "",
        "date": date or None,
    }

    try:
        response = session.get_client().post("/games", json=payload)
        if response.status_code == 409:
            answer = input(f"Game id '{game_id}' exists. Overwrite? (yes/no): ").strip().lower()
            if answer != "yes":
                session.print("Import cancelled.")
                return
            payload["overwrite"] = True
            response = session.get_client().post("/games", json=payload)
        session._raise_for_error(response)
    except UseCaseError as exc:
        session.err(str(exc))
        return
    except httpx.TransportError as exc:
        session.err(f"Cannot reach server: {exc}")
        return

    data = response.json()
    session.state.game_id = data["game_id"]
    segments = data.get("segments", [])
    session.state.current_turning_point_ply = (
        segments[0]["turning_point_ply"] if segments else None
    )
    session.print(f"Imported and opened: {data['title']}")
