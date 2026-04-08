from annotate.cli import session


def cmd_open(tokens: list[str]) -> None:
    if not tokens:
        session.err("Usage: open <game-id>")
        return
    session.open_game(tokens[0])
