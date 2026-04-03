"""chess-annotate — interactive REPL for authoring chess game annotations."""

import builtins
import readline
import sys

assert readline is not None  # Do not delete this line - needed to prevent "import readline" from being optimized away
from dataclasses import dataclass
from pathlib import Path

from annotate.adapters.json_file_annotation_repository import JSONFileAnnotationRepository
from annotate.adapters.python_chess_pgn_parser import PythonChessPGNParser
from annotate.adapters.system_editor_launcher import SystemEditorLauncher
from annotate.cli import strip_comments
from annotate.config import get_config, get_store_dir
from annotate.domain.annotation import Annotation
from annotate.domain.model import move_from_ply, ply_from_move, segment_end_ply
from annotate.use_cases.interactors import merge_segment, split_segment


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

@dataclass
class _Session:
    """Track the mutable state of one interactive CLI authoring session.

    The REPL keeps a single global instance of this data class to know
    whether an annotation is currently open and whether that in-memory
    state has unsaved changes. The ``open`` property provides the
    command loop with a simple session-state check without duplicating
    ``None`` comparisons throughout the module.
    """

    annotation: Annotation | None = None
    dirty: bool = False
    current_segment: int | None = None  # 1-based segment number

    @property
    def open(self) -> bool:
        """Return whether an annotation is currently open in the session."""
        return self.annotation is not None


_session = _Session()
_repo: JSONFileAnnotationRepository | None = None


def get_repo() -> JSONFileAnnotationRepository:
    """Return the lazily initialized repository used by the CLI session.

    The REPL shares a single repository instance for the lifetime of the
    process so command handlers do not repeatedly recreate the on-disk
    adapter or its directory checks.
    """

    global _repo
    if _repo is None:
        store_dir = get_store_dir()
        _repo = JSONFileAnnotationRepository(store_dir)
    return _repo


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print(msg: str = "") -> None:
    """Write a normal user-facing message to standard output.

    This helper centralizes CLI output and intentionally shadows the
    built-in name inside this module. It delegates to
    :func:`builtins.print` to avoid recursion.
    """

    builtins.print(msg)


def err(msg: str) -> None:
    """Write an error message to standard error with a standard prefix."""

    builtins.print(f"Error: {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Show command
# ---------------------------------------------------------------------------

def fmt_move_range(annotation: Annotation, index: int) -> str:
    """Format a segment's move span for display in the ``show`` command.

    The result uses move number plus side markers such as ``1w`` or
    ``12b`` so users see author-facing boundaries instead of raw ply
    numbers.
    """

    seg = annotation.segments[index]
    start_move, start_side = move_from_ply(seg.start_ply)
    end_ply = segment_end_ply(annotation, index)
    end_move, end_side = move_from_ply(end_ply)
    start_side_char = "w" if start_side == "white" else "b"
    end_side_char = "w" if end_side == "white" else "b"
    return f"{start_move}{start_side_char} \u2013 {end_move}{end_side_char}"


def cmd_show(_tokens: list[str]) -> None:
    """Display a list of segments with their move ranges and labels.

    Unsaved state is shown in the heading when appropriate.
    """

    ann = _session.annotation
    unsaved = "  [unsaved changes]" if _session.dirty else ""
    from annotate.domain.model import total_plies
    total = total_plies(ann.pgn)
    total_moves = (total + 1) // 2
    header = f"{ann.title}  ({ann.player_side}, {total_moves} moves){unsaved}"
    print(header)
    print()
    col_w = max(len(fmt_move_range(ann, i)) for i in range(len(ann.segments)))
    fmt = f"{{:2}}{{:>3}}  {{:<{col_w}}}  {{}}"
    print(fmt.format("", "#", "Moves", "Label"))
    for i, seg in enumerate(ann.segments):
        prefix = "* " if _session.current_segment == i + 1 else "  "
        print(fmt.format(prefix, i + 1, fmt_move_range(ann, i), seg.label))
    print()


# ---------------------------------------------------------------------------
# New command — interactive creation flow
# ---------------------------------------------------------------------------

def prompt(prompt_text: str, default: str | None = None) -> str:
    """Prompt the user for required or defaultable text input.

    When ``default`` is provided, pressing Enter accepts that default.
    Otherwise the prompt repeats until the user supplies a non-empty
    value.
    """

    if default is not None:
        text = input(f"{prompt_text} [{default}]: ").strip()
        return text if text else default
    while True:
        text = input(f"{prompt_text}: ").strip()
        if text:
            return text
        print("This field is required.")


def cmd_new(_tokens: list[str]) -> None:
    """Create a new annotation interactively from a PGN file.

    Prompts for a PGN file path first, then collects the remaining
    metadata needed to create an annotation, writes an initial working
    copy, and opens the new annotation in the current session.
    """

    while True:
        pgn_path = Path(prompt(".pgn file"))
        if pgn_path.exists():
            break
        err(f"File not found: {pgn_path}")

    pgn_text = strip_comments(pgn_path.read_text())
    parser = PythonChessPGNParser()
    try:
        info = parser.parse(pgn_text)
    except ValueError as exc:
        err(str(exc))
        return

    total_moves = (info["total_plies"] + 1) // 2
    print(
        f"PGN loaded: {info['total_plies']} plies ({total_moves} moves), "
        f"White: {info['white']}, Black: {info['black']}"
    )
    print()

    white = info["white"] if info["white"] != "?" else "N/A"
    black = info["black"] if info["black"] != "?" else "N/A"
    pgn_date_raw = info["date"].replace("?", "").strip(".") or "N/A"
    title = f"{white} - {black} {pgn_date_raw}"

    author = get_config().author or ""

    pgn_date = info["date"].replace("?", "").strip(".") or None
    date = prompt("Date", default=pgn_date or "")

    while True:
        side = prompt("You played (white/black)").lower()
        if side in ("white", "black"):
            break
        print("Please enter white or black.")

    default_orientation = "black" if side == "black" else "white"
    orientation = prompt("Diagram orientation", default=default_orientation).lower()
    if orientation not in ("white", "black"):
        orientation = default_orientation

    repo = get_repo()
    annotation = Annotation.create(
        annotation_id=repo.next_id(),
        title=title,
        author=author,
        date=date,
        pgn=pgn_text,
        player_side=side,
        diagram_orientation=orientation,
    )
    repo.save_working_copy(annotation)

    _session.annotation = annotation
    _session.dirty = True

    print()
    print(
        f"Annotation created. 1 segment spanning moves 1\u2013{total_moves} ({side})."
    )


# ---------------------------------------------------------------------------
# Open command
# ---------------------------------------------------------------------------

def cmd_open(tokens: list[str]) -> None:
    """Open an existing annotation into the current interactive session.

    If a working copy already exists, the user is asked whether to
    resume it. Otherwise the canonical saved annotation is loaded and a
    fresh working copy is created for editing.
    """

    if not tokens:
        err("Usage: open <annotation_id>")
        return

    raw = tokens[0]
    if raw.endswith(".json"):
        raw = raw[:-5]
    try:
        annotation_id = int(raw)
    except ValueError:
        err(f"Invalid annotation id: {raw!r}")
        return

    repo = get_repo()
    try:
        annotation = repo.load(annotation_id)
    except FileNotFoundError:
        err(f"Annotation not found: {annotation_id}")
        return

    if repo.exists_working_copy(annotation_id):
        print(f"Working copy found for '{annotation.title}'.")
        answer = input("Resume previous session? (yes/no): ").strip().lower()
        if answer == "yes":
            annotation = repo.load_working_copy(annotation_id)
            _session.annotation = annotation
            _session.dirty = True
            print("Resumed working copy.")
            return
        else:
            repo.discard_working_copy(annotation_id)

    repo.save_working_copy(annotation)
    _session.annotation = annotation
    _session.dirty = False
    print(f"Opened: {annotation.title}")


# ---------------------------------------------------------------------------
# List command
# ---------------------------------------------------------------------------

def cmd_list(_tokens: list[str]) -> None:
    """List all saved annotations in the repository."""

    repo = get_repo()
    entries = repo.list_all()
    if not entries:
        print("No annotations found.")
        return
    for annotation_id, title in entries:
        print(f"  {annotation_id}  {title}")


# ---------------------------------------------------------------------------
# Save / close / quit
# ---------------------------------------------------------------------------

def cmd_save(_tokens: list[str]) -> None:
    """Persist the current session's annotation to the main store.

    The current in-memory annotation is first written to the working
    copy, then committed to the canonical store file so the main copy
    and working copy remain in sync.
    """

    repo = get_repo()
    ann = _session.annotation
    repo.save_working_copy(ann)
    repo.commit_working_copy(ann.annotation_id)
    _session.dirty = False
    print("Saved.")


def do_close() -> None:
    """Close the current session and discard its working copy.

    If the session has unsaved changes, the user is prompted to save
    first. Once closing completes, the in-memory session state is reset
    and the temporary working copy is removed.
    """
    if _session.dirty:
        answer = input("You have unsaved changes. Save before closing? (yes/no): ").strip().lower()
        if answer == "yes":
            cmd_save([])
    ann = _session.annotation
    get_repo().discard_working_copy(ann.annotation_id)
    _session.annotation = None
    _session.dirty = False
    print("Session closed.")


def cmd_close(_tokens: list[str]) -> None:
    """Handle the ``close`` command by ending the current session."""

    do_close()


def cmd_quit(_tokens: list[str]) -> None:
    """Exit the REPL, closing the current session first if needed."""

    if _session.open:
        do_close()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Authoring commands (M2)
# ---------------------------------------------------------------------------

def _parse_move_side(tokens: list[str], usage: str) -> int | None:
    """Parse a single ``<number><w|b>`` token into a ply.

    Returns the ply on success, or ``None`` after printing an error
    message when the token is malformed.
    """
    if not tokens:
        err(f"Usage: {usage}")
        return None
    token = tokens[0].lower()
    if not token or token[-1] not in ("w", "b"):
        err(f"Usage: {usage}")
        return None
    try:
        move_number = int(token[:-1])
    except ValueError:
        err(f"Usage: {usage}")
        return None
    side = "white" if token[-1] == "w" else "black"
    return ply_from_move(move_number, side)


def cmd_split(tokens: list[str]) -> None:
    """Split the segment containing the given move into two segments."""
    ply = _parse_move_side(tokens, "split <move>")
    if ply is None:
        return
    label = prompt("Label for new segment")
    try:
        _session.annotation = split_segment(_session.annotation, ply, label)
        get_repo().save_working_copy(_session.annotation)
        _session.dirty = True
        print("Segment split.")
    except ValueError as exc:
        err(str(exc))


def cmd_merge(tokens: list[str]) -> None:
    """Remove the turning point at the given move, merging with the previous segment."""
    ply = _parse_move_side(tokens, "merge <move>")
    if ply is None:
        return
    try:
        annotation, merged = merge_segment(_session.annotation, ply)
    except ValueError as exc:
        err(str(exc))
        return
    if merged:
        _session.annotation = annotation
        get_repo().save_working_copy(_session.annotation)
        _session.dirty = True
        print("Segments merged.")
        return
    # Later segment has content — ask the author to confirm.
    idx = next(
        i for i, s in enumerate(_session.annotation.segments)
        if s.start_ply == ply
    )
    print(f"Segment {idx + 1} has content that will be discarded.")
    answer = input("Discard and merge anyway? (yes/no): ").strip().lower()
    if answer == "yes":
        annotation, _ = merge_segment(_session.annotation, ply, force=True)
        _session.annotation = annotation
        get_repo().save_working_copy(_session.annotation)
        _session.dirty = True
        print("Segments merged.")
    else:
        print("Merge cancelled.")


def _require_current_segment() -> int | None:
    """Return the current segment number, or print an error and return None."""
    if _session.current_segment is None:
        err("No segment selected. Use: segment <#>")
        return None
    return _session.current_segment


def cmd_segment(tokens: list[str]) -> None:
    """Set the current segment by its 1-based segment number."""
    if not tokens:
        err("Usage: segment <#>")
        return
    try:
        seg_num = int(tokens[0])
    except ValueError:
        err(f"Segment number must be an integer, got {tokens[0]!r}")
        return
    segments = _session.annotation.segments
    if not (1 <= seg_num <= len(segments)):
        err(f"Segment number must be between 1 and {len(segments)}")
        return
    _session.current_segment = seg_num
    print(f"Current segment: {seg_num} — {segments[seg_num - 1].label}")


def cmd_label(tokens: list[str]) -> None:
    """Set or replace the label for the current segment."""
    seg_num = _require_current_segment()
    if seg_num is None:
        return
    if not tokens:
        err("Usage: label <text>")
        return
    segments = _session.annotation.segments
    segments[seg_num - 1].label = " ".join(tokens)
    _session.dirty = True
    print(f"Label updated for segment {seg_num}.")


def cmd_diagram(tokens: list[str]) -> None:
    """Toggle the end-of-segment diagram for the current segment on or off."""
    seg_num = _require_current_segment()
    if seg_num is None:
        return
    if not tokens or tokens[0].lower() not in ("on", "off"):
        err("Usage: diagram on|off")
        return
    toggle = tokens[0].lower()
    segments = _session.annotation.segments
    segments[seg_num - 1].show_diagram = toggle == "on"
    _session.dirty = True
    print(f"Diagram {'enabled' if toggle == 'on' else 'disabled'} for segment {seg_num}.")


def cmd_orientation(tokens: list[str]) -> None:
    """Set the diagram orientation for the annotation."""
    if not tokens or tokens[0].lower() not in ("white", "black"):
        err("Usage: orientation <white|black>")
        return
    _session.annotation.diagram_orientation = tokens[0].lower()
    _session.dirty = True
    print(f"Diagram orientation set to {tokens[0].lower()}.")


def import_pgn_to_lichess(pgn: str) -> str:
    """Import a PGN to Lichess and return the game URL."""
    import requests
    response = requests.post(
        "https://lichess.org/api/import",
        data={"pgn": pgn},
    )
    response.raise_for_status()
    return response.url


def cmd_see(_tokens: list[str]) -> None:
    """Open Lichess analysis for the current game."""
    import webbrowser

    ann = _session.annotation
    url = import_pgn_to_lichess(ann.pgn)
    webbrowser.open(url)
    print("Opening Lichess analysis.")


def cmd_json(_tokens: list[str]) -> None:
    """Print the current annotation's JSON representation to standard output."""
    from annotate.adapters.json_file_annotation_repository import to_dict
    import json
    print(json.dumps(to_dict(_session.annotation), indent=2))


def cmd_comment(_tokens: list[str]) -> None:
    """Open $EDITOR to write or edit commentary for the current segment."""
    seg_num = _require_current_segment()
    if seg_num is None:
        return
    segments = _session.annotation.segments
    seg = segments[seg_num - 1]
    launcher = SystemEditorLauncher()
    updated = launcher.edit(seg.commentary)
    seg.commentary = updated
    _session.dirty = True
    print(f"Commentary updated for segment {seg_num}.")


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

_HELP_NO_SESSION = """\
Commands (no session open):
  new              Create a new annotation (prompts for PGN file and metadata)
  open <id>        Open an existing annotation
  list             List all annotations
  help             Show this help
  quit             Exit"""

_HELP_SESSION = """\
Commands (session open):
  show                        List segments with their labels
  segment <#>                 Set the current segment
  split <move>                Add a turning point; split the containing segment
  merge <move>                Remove a turning point; merge with previous segment
  label <text>                Set or update the label for the current segment
  comment                     Open $EDITOR to write commentary for the current segment
  diagram on|off              Toggle the end-of-segment diagram for the current segment
  orientation <white|black>   Set the diagram orientation for this annotation
  see                         Open Lichess analysis for this game
  json                        Print the current annotation as JSON
  save                        Save to main store (stay in session)
  close                       Close session (prompts if unsaved changes)
  help                        Show this help
  quit                        Close session and exit"""


def cmd_help(_tokens: list[str]) -> None:
    """Print the help text appropriate to the current session state."""

    if _session.open:
        print(_HELP_SESSION)
    else:
        print(_HELP_NO_SESSION)


# ---------------------------------------------------------------------------
# Command tables
# ---------------------------------------------------------------------------

_COMMANDS_NO_SESSION: dict[str, tuple] = {
    "new": (cmd_new, False),
    "open": (cmd_open, False),
    "list": (cmd_list, False),
    "help": (cmd_help, False),
    "quit": (cmd_quit, False),
}

_COMMANDS_SESSION: dict[str, tuple] = {
    "show": (cmd_show, True),
    "segment": (cmd_segment, True),
    "split": (cmd_split, True),
    "merge": (cmd_merge, True),
    "label": (cmd_label, True),
    "comment": (cmd_comment, True),
    "diagram": (cmd_diagram, True),
    "orientation": (cmd_orientation, True),
    "see": (cmd_see, True),
    "json": (cmd_json, True),
    "save": (cmd_save, True),
    "close": (cmd_close, True),
    "help": (cmd_help, True),
    "quit": (cmd_quit, True),
}


# ---------------------------------------------------------------------------
# Crash recovery
# ---------------------------------------------------------------------------

def check_stale_working_copies() -> None:
    """Offer recovery for any leftover working copies from prior sessions.

    At startup, the CLI scans for working copies that may have been left
    behind by a crash or interrupted session. Each one is offered to the
    user for resume-or-discard handling before normal command processing
    begins.
    """

    repo = get_repo()
    stale = repo.stale_working_copies()
    if not stale:
        return
    for annotation_id in stale:
        try:
            ann = repo.load_working_copy(annotation_id)
        except Exception:
            repo.discard_working_copy(annotation_id)
            continue
        print(f"Working copy found for '{ann.title}' (from a previous session).")
        answer = input("Resume? (yes/no): ").strip().lower()
        if answer == "yes":
            _session.annotation = ann
            _session.dirty = True
            print("Resumed.")
            return
        else:
            repo.discard_working_copy(annotation_id)
            print("Discarded.")


# ---------------------------------------------------------------------------
# Main REPL loop
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the interactive ``chess-annotate`` REPL.

    This function prints the initial banner, performs crash-recovery
    checks for stale working copies, and then loops reading and
    dispatching commands until the process exits.
    """

    print("Chess Annotation System")
    print("Type 'help' for a list of commands.")
    print()

    check_stale_working_copies()

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            cmd_quit([])

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
                print("Not available — an annotation is already open.")
            else:
                print(f"Unknown command: {cmd_name!r}. Type 'help' for a list.")
        else:
            if cmd_name in _COMMANDS_NO_SESSION:
                handler, _ = _COMMANDS_NO_SESSION[cmd_name]
                handler(tokens)
            elif cmd_name in _COMMANDS_SESSION:
                print("Not available — no annotation is open.")
            else:
                print(f"Unknown command: {cmd_name!r}. Type 'help' for a list.")
