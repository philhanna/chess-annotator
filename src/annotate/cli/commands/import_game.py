from pathlib import Path

from annotate.adapters.python_chess_pgn_parser import PythonChessPGNParser
from annotate.cli import strip_comments
from annotate.cli import session
from annotate.use_cases import OverwriteRequiredError, UseCaseError


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

    try:
        game_state = session.get_service().import_game(
            game_id=game_id,
            pgn_text=raw_pgn,
            player_side=side,
            author=session.get_config().author or "",
            date=date,
        )
    except OverwriteRequiredError:
        answer = input(f"Game id '{game_id}' exists. Overwrite? (yes/no): ").strip().lower()
        if answer != "yes":
            session.print("Import cancelled.")
            return
        game_state = session.get_service().import_game(
            game_id=game_id,
            pgn_text=raw_pgn,
            player_side=side,
            author=session.get_config().author or "",
            date=date,
            overwrite=True,
        )
    except UseCaseError as exc:
        session.err(str(exc))
        return

    session.state.game_id = game_state.game_id
    session.state.current_turning_point_ply = game_state.segments[0].turning_point_ply
    session.print(f"Imported and opened: {game_state.title}")
