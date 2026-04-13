import readline
import threading
import time

assert readline is not None  # Do not delete this line - needed to prevent "import readline" from being optimized away

import httpx
import uvicorn

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
from annotate.config import get_config

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


def _ensure_server_running() -> None:
    """Start the API server in a background daemon thread if it is not already running.

    Probes ``GET /health`` first. If the server is reachable the function returns
    immediately. Otherwise it starts uvicorn in a daemon thread and waits up to
    two seconds for the server to become ready.
    """
    config = get_config()
    health_url = f"{config.server_url.rstrip('/')}/health"

    # Check whether a server is already listening.
    try:
        httpx.get(health_url, timeout=0.5)
        return  # Server is already up.
    except httpx.TransportError:
        pass  # Not running — start it.

    from annotate.server.app import create_app

    server_config = uvicorn.Config(
        create_app(),
        host="127.0.0.1",
        port=8765,
        log_level="warning",
    )
    server = uvicorn.Server(server_config)
    server.install_signal_handlers = False  # Required when not running on the main thread.
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait until the server signals it is ready (up to 2 seconds).
    for _ in range(20):
        try:
            httpx.get(health_url, timeout=0.1)
            return
        except httpx.TransportError:
            time.sleep(0.1)

    session.err("Warning: server did not become ready in time.")


def check_stale_working_copies() -> None:
    """On startup, offer to resume any games that have leftover working-copy files.

    Iterates through all games with stale working files and prompts the user to
    resume each one. Discards the working files if the user declines. At most one
    game is opened (the first one the user accepts); the function returns immediately
    after an accepted resumption.
    """
    try:
        response = session.get_client().get("/games")
        session._raise_for_error(response)
        games = response.json()
    except Exception:
        return  # If the server is unreachable, skip the stale-copy check.

    for game in games:
        if not game.get("in_progress"):
            continue
        game_id = game["game_id"]
        title = game["title"]
        session.print(f"Working copy found for '{title}' ({game_id}).")
        answer = input("Resume? (yes/no): ").strip().lower()
        if answer == "yes":
            session.open_game(game_id)
            return  # Open only one game at startup.
        # Discard the working copy.
        try:
            session.get_client().delete(
                f"/games/{game_id}/session",
                params={"save_changes": "false"},
            )
        except Exception:
            pass
        session.print("Discarded.")


def main() -> None:
    """Entry point for the ``chess-annotate`` interactive REPL.

    Prints a welcome banner, ensures the API server is running, checks for stale
    working copies from previous sessions, then enters the main command loop.
    The loop reads one line at a time, dispatches to the appropriate command handler,
    and repeats until the user quits.
    """
    session.print("Chess Annotation System")
    session.print("Type 'help' for a list of commands.")
    session.print()

    _ensure_server_running()
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
