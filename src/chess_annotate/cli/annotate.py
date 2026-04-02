# chess_annotate.cli.annotate
"""chess-annotate — interactive REPL for authoring chess game annotations."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from chess_annotate.adapters.pgn_parser import PythonChessPGNParser
from chess_annotate.adapters.repository import JSONFileAnnotationRepository
from chess_annotate.config import get_store_dir
from chess_annotate.domain.model import Annotation, move_from_ply, segment_end_ply


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

@dataclass
class _Session:
    annotation: Annotation | None = None
    dirty: bool = False

    @property
    def open(self) -> bool:
        return self.annotation is not None


_session = _Session()
_repo: JSONFileAnnotationRepository | None = None


def _get_repo() -> JSONFileAnnotationRepository:
    global _repo
    if _repo is None:
        store_dir = get_store_dir()
        _repo = JSONFileAnnotationRepository(store_dir)
    return _repo


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print(msg: str = "") -> None:
    print(msg)


def _err(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Show command
# ---------------------------------------------------------------------------

def _fmt_move_range(annotation: Annotation, index: int) -> str:
    seg = annotation.segments[index]
    start_move, start_side = move_from_ply(seg.start_ply)
    end_ply = segment_end_ply(annotation, index)
    end_move, end_side = move_from_ply(end_ply)
    start_side_char = "w" if start_side == "white" else "b"
    end_side_char = "w" if end_side == "white" else "b"
    return f"{start_move}{start_side_char} \u2013 {end_move}{end_side_char}"


def _cmd_show(_tokens: list[str]) -> None:
    ann = _session.annotation
    unsaved = "  [unsaved changes]" if _session.dirty else ""
    from chess_annotate.domain.model import total_plies
    total = total_plies(ann.pgn)
    total_moves = (total + 1) // 2
    side_label = ann.player_side
    header = f"{ann.title}  ({side_label}, {total_moves} moves){unsaved}"
    _print(header)
    _print()
    col_w = max(len(_fmt_move_range(ann, i)) for i in range(len(ann.segments)))
    label_w = max(
        (len(seg.label) if seg.label else len("(no label)"))
        for seg in ann.segments
    )
    label_w = max(label_w, len("Label"))
    fmt = f"  {{:>3}}  {{:<{col_w}}}  {{:<{label_w}}}  {{:<11}}  {{}}"
    _print(fmt.format("#", "Moves", "Label", "Commentary", "Diagram"))
    for i, seg in enumerate(ann.segments):
        label = seg.label if seg.label else "(no label)"
        commentary = "yes" if seg.commentary.strip() else "no"
        diagram = "yes" if seg.show_diagram else "no"
        _print(fmt.format(i + 1, _fmt_move_range(ann, i), label, commentary, diagram))
    _print()


# ---------------------------------------------------------------------------
# New command — interactive creation flow
# ---------------------------------------------------------------------------

def _prompt(prompt_text: str, default: str | None = None) -> str:
    if default is not None:
        text = input(f"{prompt_text} [{default}]: ").strip()
        return text if text else default
    while True:
        text = input(f"{prompt_text}: ").strip()
        if text:
            return text
        _print("This field is required.")


def _cmd_new(tokens: list[str]) -> None:
    if not tokens:
        _err("Usage: new <path/to/game.pgn>")
        return

    pgn_path = Path(tokens[0])
    if not pgn_path.exists():
        _err(f"File not found: {pgn_path}")
        return

    pgn_text = pgn_path.read_text()
    parser = PythonChessPGNParser()
    try:
        info = parser.parse(pgn_text)
    except ValueError as exc:
        _err(str(exc))
        return

    total_moves = (info["total_plies"] + 1) // 2
    _print(
        f"PGN loaded: {info['total_plies']} plies ({total_moves} moves), "
        f"White: {info['white']}, Black: {info['black']}"
    )
    _print()

    title = _prompt("Title")
    author = _prompt("Author")

    pgn_date = info["date"].replace("??", "").strip(".") or None
    date = _prompt("Date", default=pgn_date or "")

    while True:
        side = _prompt("You played (white/black/none)").lower()
        if side in ("white", "black", "none"):
            break
        _print("Please enter white, black, or none.")

    default_orientation = "black" if side == "black" else "white"
    orientation = _prompt("Diagram orientation", default=default_orientation).lower()
    if orientation not in ("white", "black"):
        orientation = default_orientation

    annotation = Annotation.create(
        title=title,
        author=author,
        date=date,
        pgn=pgn_text,
        player_side=side,
        diagram_orientation=orientation,
    )

    repo = _get_repo()
    repo.save_working_copy(annotation)

    _session.annotation = annotation
    _session.dirty = True

    _print()
    _print(
        f"Annotation created. 1 segment spanning moves 1\u2013{total_moves} ({side})."
    )


# ---------------------------------------------------------------------------
# Open command
# ---------------------------------------------------------------------------

def _cmd_open(tokens: list[str]) -> None:
    if not tokens:
        _err("Usage: open <annotation_id>")
        return

    annotation_id = tokens[0]
    # Strip .json suffix if the user typed the filename
    if annotation_id.endswith(".json"):
        annotation_id = annotation_id[:-5]

    repo = _get_repo()
    try:
        annotation = repo.load(annotation_id)
    except FileNotFoundError:
        _err(f"Annotation not found: {annotation_id}")
        return

    if repo.exists_working_copy(annotation_id):
        _print(f"Working copy found for '{annotation.title}'.")
        answer = input("Resume previous session? (yes/no): ").strip().lower()
        if answer == "yes":
            annotation = repo.load_working_copy(annotation_id)
            _session.annotation = annotation
            _session.dirty = True
            _print("Resumed working copy.")
            return
        else:
            repo.discard_working_copy(annotation_id)

    repo.save_working_copy(annotation)
    _session.annotation = annotation
    _session.dirty = False
    _print(f"Opened: {annotation.title}")


# ---------------------------------------------------------------------------
# List command
# ---------------------------------------------------------------------------

def _cmd_list(_tokens: list[str]) -> None:
    repo = _get_repo()
    entries = repo.list_all()
    if not entries:
        _print("No annotations found.")
        return
    for annotation_id, title in entries:
        _print(f"  {annotation_id}  {title}")


# ---------------------------------------------------------------------------
# Save / close / quit
# ---------------------------------------------------------------------------

def _cmd_save(_tokens: list[str]) -> None:
    repo = _get_repo()
    ann = _session.annotation
    repo.save_working_copy(ann)
    repo.commit_working_copy(ann.annotation_id)
    _session.dirty = False
    _print("Saved.")


def _do_close() -> None:
    """Close the session, prompting to save if dirty. Returns after closing."""
    if _session.dirty:
        answer = input("You have unsaved changes. Save before closing? (yes/no): ").strip().lower()
        if answer == "yes":
            _cmd_save([])
    ann = _session.annotation
    _get_repo().discard_working_copy(ann.annotation_id)
    _session.annotation = None
    _session.dirty = False
    _print("Session closed.")


def _cmd_close(_tokens: list[str]) -> None:
    _do_close()


def _cmd_quit(_tokens: list[str]) -> None:
    if _session.open:
        _do_close()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

_HELP_NO_SESSION = """\
Commands (no session open):
  new <path>       Create a new annotation from a PGN file
  open <id>        Open an existing annotation
  list             List all annotations
  help             Show this help
  quit             Exit"""

_HELP_SESSION = """\
Commands (session open):
  show             Display current annotation state
  save             Save to main store (stay in session)
  close            Close session (prompts if unsaved changes)
  help             Show this help
  quit             Close session and exit"""


def _cmd_help(_tokens: list[str]) -> None:
    if _session.open:
        _print(_HELP_SESSION)
    else:
        _print(_HELP_NO_SESSION)


# ---------------------------------------------------------------------------
# Command tables
# ---------------------------------------------------------------------------

_COMMANDS_NO_SESSION: dict[str, tuple] = {
    "new": (_cmd_new, False),
    "open": (_cmd_open, False),
    "list": (_cmd_list, False),
    "help": (_cmd_help, False),
    "quit": (_cmd_quit, False),
}

_COMMANDS_SESSION: dict[str, tuple] = {
    "show": (_cmd_show, True),
    "save": (_cmd_save, True),
    "close": (_cmd_close, True),
    "help": (_cmd_help, True),
    "quit": (_cmd_quit, True),
}


# ---------------------------------------------------------------------------
# Crash recovery
# ---------------------------------------------------------------------------

def _check_stale_working_copies() -> None:
    repo = _get_repo()
    stale = repo.stale_working_copies()
    if not stale:
        return
    for annotation_id in stale:
        try:
            ann = repo.load_working_copy(annotation_id)
        except Exception:
            repo.discard_working_copy(annotation_id)
            continue
        _print(f"Working copy found for '{ann.title}' (from a previous session).")
        answer = input("Resume? (yes/no): ").strip().lower()
        if answer == "yes":
            _session.annotation = ann
            _session.dirty = True
            _print("Resumed.")
            return
        else:
            repo.discard_working_copy(annotation_id)
            _print("Discarded.")


# ---------------------------------------------------------------------------
# Main REPL loop
# ---------------------------------------------------------------------------

def main() -> None:
    _print("Chess Annotation System")
    _print("Type 'help' for a list of commands.")
    _print()

    _check_stale_working_copies()

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            _print()
            _cmd_quit([])

        if not line:
            continue

        parts = line.split(None, 1)
        cmd_name = parts[0].lower()
        tokens = parts[1].split() if len(parts) > 1 else []

        if _session.open:
            if cmd_name in _COMMANDS_SESSION:
                handler, _ = _COMMANDS_SESSION[cmd_name]
                handler(tokens)
            elif cmd_name in _COMMANDS_NO_SESSION:
                _print("Not available — an annotation is already open.")
            else:
                _print(f"Unknown command: {cmd_name!r}. Type 'help' for a list.")
        else:
            if cmd_name in _COMMANDS_NO_SESSION:
                handler, _ = _COMMANDS_NO_SESSION[cmd_name]
                handler(tokens)
            elif cmd_name in _COMMANDS_SESSION:
                _print("Not available — no annotation is open.")
            else:
                _print(f"Unknown command: {cmd_name!r}. Type 'help' for a list.")
