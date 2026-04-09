import readline

assert readline is not None  # Do not delete this line - needed to prevent "import readline" from being optimized away

from annotate.cli import session
from annotate.cli.commands import (
    cmd_close,
    cmd_edit,
    cmd_copy,
    cmd_delete,
    cmd_diagram,
    cmd_help,
    cmd_import,
    cmd_json,
    cmd_label,
    cmd_list,
    cmd_list_segments,
    cmd_merge,
    cmd_open,
    cmd_quit,
    cmd_render,
    cmd_save,
    cmd_see,
    cmd_select,
    cmd_split,
    cmd_view,
)

# Commands available when no game session is open.
_COMMANDS_NO_SESSION = {
    "import": cmd_import,
    "open": cmd_open,
    "list": cmd_list,
    "copy": cmd_copy,
    "delete": cmd_delete,
    "render": cmd_render,
    "see": cmd_see,
    "help": cmd_help,
    "quit": cmd_quit,
}

# Commands available when a game session is open (supersedes the no-session table).
_COMMANDS_SESSION = {
    "list": cmd_list_segments,
    "view": cmd_view,
    "split": cmd_split,
    "merge": cmd_merge,
    "label": cmd_label,
    "edit": cmd_edit,
    "diagram": cmd_diagram,
    "save": cmd_save,
    "close": cmd_close,
    "copy": cmd_copy,
    "render": cmd_render,
    "see": cmd_see,
    "json": cmd_json,
    "help": cmd_help,
    "quit": cmd_quit,
}


def check_stale_working_copies() -> None:
    """On startup, offer to resume any games that have leftover working-copy files.

    Iterates through all games with stale working files and prompts the user to
    resume each one. Discards the working files if the user declines. At most one
    game is opened (the first one the user accepts); the function returns immediately
    after an accepted resumption.
    """
    repo = session.get_repo()
    stale = repo.stale_working_copies()
    if not stale:
        return
    for game_id in stale:
        try:
            annotation = repo.load_working_copy(game_id)
        except Exception:
            # If the working copy is unreadable, discard it and move on.
            repo.discard_working_copy(game_id)
            continue
        session.print(f"Working copy found for '{annotation.title}' ({game_id}).")
        answer = input("Resume? (yes/no): ").strip().lower()
        if answer == "yes":
            session.open_game(game_id)
            return  # Open only one game at startup.
        repo.discard_working_copy(game_id)
        session.print("Discarded.")


def main() -> None:
    """Entry point for the ``chess-annotate`` interactive REPL.

    Prints a welcome banner, checks for stale working copies from previous
    sessions, then enters the main command loop. The loop reads one line at a
    time, dispatches to the appropriate command handler, and repeats until the
    user quits.
    """
    session.print("Chess Annotation System")
    session.print("Type 'help' for a list of commands.")
    session.print()

    check_stale_working_copies()

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl-D / Ctrl-C gracefully by treating them as a quit.
            session.print()
            cmd_quit([])
            continue

        if not line:
            continue

        # Split into the command name and remaining tokens.
        parts = line.split(None, 1)
        cmd_name = parts[0].lower()
        tokens = parts[1].split() if len(parts) > 1 else []

        # Choose the command table based on whether a session is open.
        table = _COMMANDS_SESSION if session.state.open else _COMMANDS_NO_SESSION

        # When a session is open, a bare number selects a segment by index.
        if session.state.open and cmd_name.isdigit():
            cmd_select([cmd_name] + tokens)
            continue

        handler = table.get(cmd_name)
        if handler is None:
            session.print(f"Unknown command: {cmd_name!r}. Type 'help' for a list.")
            continue
        handler(tokens)
