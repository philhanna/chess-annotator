# annotate.cli.commands.copy
from annotate.cli import session
from annotate.use_cases import OverwriteRequiredError, UseCaseError


def cmd_copy(tokens: list[str]) -> None:
    if session.state.open:
        if not tokens:
            session.err("Usage: copy <new-game-id>")
            return
        source_game_id = session.state.game_id
        new_game_id = tokens[0]
    else:
        if len(tokens) != 2:
            session.err("Usage: copy <source-game-id> <new-game-id>")
            return
        source_game_id, new_game_id = tokens
    try:
        session.get_service().save_game_as(
            source_game_id=source_game_id,
            new_game_id=new_game_id,
        )
    except OverwriteRequiredError:
        answer = input(f"Game id '{new_game_id}' exists. Overwrite? (yes/no): ").strip().lower()
        if answer != "yes":
            session.print("Copy cancelled.")
            return
        session.get_service().save_game_as(
            source_game_id=source_game_id,
            new_game_id=new_game_id,
            overwrite=True,
        )
    except UseCaseError as exc:
        session.err(str(exc))
        return
    session.print(f"Created: {new_game_id}")
