"""chess-annotate — interactive REPL for authoring chess game annotations."""

import builtins
import json
import readline
import sys
import webbrowser

assert readline is not None  # Do not delete this line - needed to prevent "import readline" from being optimized away
from dataclasses import dataclass
from pathlib import Path

from annotate.adapters.json_file_annotation_repository import JSONFileAnnotationRepository
from annotate.adapters.lichess_api_uploader import LichessAPIUploader
from annotate.adapters.markdown_html_pdf_renderer import MarkdownHTMLPDFRenderer
from annotate.adapters.python_chess_diagram_renderer import PythonChessDiagramRenderer
from annotate.adapters.python_chess_pgn_parser import PythonChessPGNParser
from annotate.adapters.system_editor_launcher import SystemEditorLauncher
from annotate.cli import strip_comments
from annotate.config import get_config, get_store_dir
from annotate.domain.model import ply_from_move
from annotate.use_cases import (
    AnnotationService,
    GameNotFoundError,
    OverwriteRequiredError,
    SegmentNotFoundError,
    SessionNotOpenError,
    UseCaseError,
)


@dataclass
class _Session:
    game_id: str | None = None
    current_turning_point_ply: int | None = None

    @property
    def open(self) -> bool:
        return self.game_id is not None


_session = _Session()
_repo: JSONFileAnnotationRepository | None = None
_service: AnnotationService | None = None


def get_repo() -> JSONFileAnnotationRepository:
    global _repo
    if _repo is None:
        _repo = JSONFileAnnotationRepository(get_store_dir())
    return _repo


def get_service() -> AnnotationService:
    global _service
    if _service is None:
        config = get_config()
        _service = AnnotationService(
            repository=get_repo(),
            pgn_parser=PythonChessPGNParser(),
            store_dir=config.store_dir,
            document_renderer=MarkdownHTMLPDFRenderer(),
            lichess_uploader=LichessAPIUploader(),
            diagram_renderer=PythonChessDiagramRenderer(),
        )
    return _service


def print(msg: str = "") -> None:
    builtins.print(msg)


def err(msg: str) -> None:
    builtins.print(f"Error: {msg}", file=sys.stderr)


def prompt(prompt_text: str, default: str | None = None) -> str:
    if default is not None:
        text = input(f"{prompt_text} [{default}]: ").strip()
        return text if text else default
    while True:
        text = input(f"{prompt_text}: ").strip()
        if text:
            return text
        print("This field is required.")


def _parse_move_side(tokens: list[str], usage: str) -> int | None:
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


def _require_open_session() -> str | None:
    if not _session.open:
        err("No game is open.")
        return None
    return _session.game_id


def _current_segments():
    game_id = _require_open_session()
    if game_id is None:
        return None
    return get_service().list_segments(game_id=game_id)


def _current_segment_summary():
    segments = _current_segments()
    if not segments:
        return None
    if _session.current_turning_point_ply is None:
        _session.current_turning_point_ply = segments[0].turning_point_ply
    for segment in segments:
        if segment.turning_point_ply == _session.current_turning_point_ply:
            return segment
    _session.current_turning_point_ply = segments[0].turning_point_ply
    return segments[0]


def _print_segment_list() -> None:
    game_id = _require_open_session()
    if game_id is None:
        return
    state = get_service().open_game(game_id)
    unsaved = "  [unsaved changes]" if state.has_unsaved_changes else ""
    print(f"{state.title}  ({game_id}){unsaved}")
    print()
    print(" #   Range       Label")
    for index, segment in enumerate(state.segments, start=1):
        marker = "* " if segment.turning_point_ply == _session.current_turning_point_ply else "  "
        print(f"{marker}{index:>2}  {segment.move_range:<10}  {segment.label or '(blank)'}")
    print()


def _open_game(game_id: str) -> None:
    try:
        state = get_service().open_game(game_id)
    except GameNotFoundError as exc:
        err(str(exc))
        return
    except UseCaseError as exc:
        err(str(exc))
        return

    _session.game_id = state.game_id
    _session.current_turning_point_ply = (
        state.segments[0].turning_point_ply if state.segments else None
    )
    print(f"Opened: {state.title}{' (resumed)' if state.resumed else ''}")


def cmd_import(_tokens: list[str]) -> None:
    while True:
        pgn_path = Path(prompt(".pgn file"))
        if pgn_path.exists():
            break
        err(f"File not found: {pgn_path}")

    raw_pgn = pgn_path.read_text()
    cleaned_pgn = strip_comments(raw_pgn)
    parser = PythonChessPGNParser()
    try:
        info = parser.parse(cleaned_pgn)
    except ValueError as exc:
        err(str(exc))
        return

    total_moves = (info["total_plies"] + 1) // 2
    print(
        f"PGN loaded: {info['total_plies']} plies ({total_moves} moves), "
        f"White: {info['white']}, Black: {info['black']}"
    )
    print()

    game_id = prompt("Game id")
    pgn_date = info["date"].replace("?", "").strip(".") or ""
    date = prompt("Date", default=pgn_date)
    while True:
        side = prompt("You played (white/black)").lower()
        if side in ("white", "black"):
            break
        print("Please enter white or black.")
    default_orientation = "black" if side == "black" else "white"
    orientation = prompt("Diagram orientation", default=default_orientation).lower()
    if orientation not in ("white", "black"):
        orientation = default_orientation

    try:
        state = get_service().import_game(
            game_id=game_id,
            pgn_text=raw_pgn,
            player_side=side,
            author=get_config().author or "",
            date=date,
            diagram_orientation=orientation,
        )
    except OverwriteRequiredError:
        answer = input(f"Game id '{game_id}' exists. Overwrite? (yes/no): ").strip().lower()
        if answer != "yes":
            print("Import cancelled.")
            return
        state = get_service().import_game(
            game_id=game_id,
            pgn_text=raw_pgn,
            player_side=side,
            author=get_config().author or "",
            date=date,
            diagram_orientation=orientation,
            overwrite=True,
        )
    except UseCaseError as exc:
        err(str(exc))
        return

    _session.game_id = state.game_id
    _session.current_turning_point_ply = state.segments[0].turning_point_ply
    print(f"Imported and opened: {state.title}")


def cmd_new(tokens: list[str]) -> None:
    cmd_import(tokens)


def cmd_open(tokens: list[str]) -> None:
    if not tokens:
        err("Usage: open <game-id>")
        return
    _open_game(tokens[0])


def cmd_list(_tokens: list[str]) -> None:
    summaries = get_service().list_games()
    if not summaries:
        print("No games found.")
        return
    for game in summaries:
        status = " [in progress]" if game.in_progress else ""
        print(
            f"{game.game_id}  {game.white} vs {game.black}  "
            f"{game.event}  {game.date}  {game.result}{status}"
        )


def cmd_segments(_tokens: list[str]) -> None:
    try:
        _print_segment_list()
    except SessionNotOpenError as exc:
        err(str(exc))


def _parse_segment_selector(token: str):
    segments = _current_segments()
    if not segments:
        return None
    try:
        index = int(token)
    except ValueError:
        err("Segment must be selected by its number.")
        return None
    if not (1 <= index <= len(segments)):
        err(f"Segment number must be between 1 and {len(segments)}")
        return None
    return segments[index - 1]


def cmd_view(tokens: list[str]) -> None:
    if not tokens:
        err("Usage: view <segment-number>")
        return
    summary = _parse_segment_selector(tokens[0])
    if summary is None:
        return
    game_id = _require_open_session()
    if game_id is None:
        return
    try:
        detail = get_service().view_segment(
            game_id=game_id,
            turning_point_ply=summary.turning_point_ply,
        )
    except (SessionNotOpenError, SegmentNotFoundError, UseCaseError) as exc:
        err(str(exc))
        return

    _session.current_turning_point_ply = detail.turning_point_ply
    print(f"Segment {tokens[0]}  {detail.move_range}")
    print(f"Label: {detail.label or '(blank)'}")
    print(f"Moves: {detail.move_list}")
    print(f"Diagram: {'on' if detail.show_diagram else 'off'}")
    print()
    print(detail.annotation or "(no annotation)")
    if detail.diagram_path is not None:
        print()
        print(f"Diagram preview: {detail.diagram_path}")


def cmd_split(tokens: list[str]) -> None:
    game_id = _require_open_session()
    if game_id is None:
        return
    ply = _parse_move_side(tokens, "split <move><w|b> [label]")
    if ply is None:
        return
    label = " ".join(tokens[1:]).strip() if len(tokens) > 1 else prompt("Label for new segment", default="")
    try:
        segments = get_service().add_turning_point(game_id=game_id, ply=ply, label=label)
    except UseCaseError as exc:
        err(str(exc))
        return
    for segment in segments:
        if segment.turning_point_ply == ply:
            _session.current_turning_point_ply = ply
            break
    print("Segment split.")


def cmd_merge(tokens: list[str]) -> None:
    game_id = _require_open_session()
    if game_id is None:
        return
    ply = _parse_move_side(tokens, "merge <move><w|b>")
    if ply is None:
        return
    try:
        get_service().remove_turning_point(game_id=game_id, ply=ply)
        print("Segments merged.")
        return
    except UseCaseError as exc:
        if "force is required" not in str(exc):
            err(str(exc))
            return
    answer = input("Segment content will be discarded. Merge anyway? (yes/no): ").strip().lower()
    if answer != "yes":
        print("Merge cancelled.")
        return
    try:
        get_service().remove_turning_point(game_id=game_id, ply=ply, force=True)
    except UseCaseError as exc:
        err(str(exc))
        return
    print("Segments merged.")


def cmd_label(tokens: list[str]) -> None:
    game_id = _require_open_session()
    if game_id is None:
        return
    current = _current_segment_summary()
    if current is None:
        err("No current segment.")
        return
    if not tokens:
        err("Usage: label <text>")
        return
    try:
        get_service().set_segment_label(
            game_id=game_id,
            turning_point_ply=current.turning_point_ply,
            label=" ".join(tokens),
        )
    except UseCaseError as exc:
        err(str(exc))
        return
    print("Label updated.")


def cmd_comment(_tokens: list[str]) -> None:
    game_id = _require_open_session()
    if game_id is None:
        return
    current = _current_segment_summary()
    if current is None:
        err("No current segment.")
        return
    detail = get_service().view_segment(
        game_id=game_id,
        turning_point_ply=current.turning_point_ply,
    )
    launcher = SystemEditorLauncher()
    updated = launcher.edit(detail.annotation)
    try:
        get_service().set_segment_annotation(
            game_id=game_id,
            turning_point_ply=current.turning_point_ply,
            annotation_text=updated,
        )
    except UseCaseError as exc:
        err(str(exc))
        return
    print("Annotation updated.")


def cmd_diagram(tokens: list[str]) -> None:
    game_id = _require_open_session()
    if game_id is None:
        return
    current = _current_segment_summary()
    if current is None:
        err("No current segment.")
        return
    desired = None
    if tokens:
        if tokens[0].lower() not in ("on", "off"):
            err("Usage: diagram [on|off]")
            return
        desired = tokens[0].lower() == "on"
    try:
        detail = get_service().view_segment(
            game_id=game_id,
            turning_point_ply=current.turning_point_ply,
        )
        if desired is None:
            updated = get_service().toggle_segment_diagram(
                game_id=game_id,
                turning_point_ply=current.turning_point_ply,
            )
        elif detail.show_diagram != desired:
            updated = get_service().toggle_segment_diagram(
                game_id=game_id,
                turning_point_ply=current.turning_point_ply,
            )
        else:
            updated = detail
    except UseCaseError as exc:
        err(str(exc))
        return
    print(f"Diagram {'enabled' if updated.show_diagram else 'disabled'}.")


def cmd_save(_tokens: list[str]) -> None:
    game_id = _require_open_session()
    if game_id is None:
        return
    try:
        get_service().save_session(game_id)
    except UseCaseError as exc:
        err(str(exc))
        return
    print("Saved.")


def _do_close() -> bool:
    game_id = _require_open_session()
    if game_id is None:
        return False
    try:
        result = get_service().close_game(game_id, save_changes=None)
    except UseCaseError as exc:
        err(str(exc))
        return False
    if result.requires_confirmation:
        answer = input("You have unsaved changes. Save before closing? (yes/no/cancel): ").strip().lower()
        if answer == "cancel":
            print("Close cancelled.")
            return False
        save_changes = answer == "yes"
        result = get_service().close_game(game_id, save_changes=save_changes)
    _session.game_id = None
    _session.current_turning_point_ply = None
    print("Session closed.")
    return True


def cmd_close(_tokens: list[str]) -> None:
    _do_close()


def cmd_render(tokens: list[str]) -> None:
    game_id = tokens[0] if tokens else _require_open_session()
    if game_id is None:
        err("Usage: render <game-id>")
        return
    config = get_config()
    try:
        output_path = get_service().render_pdf(
            game_id=game_id,
            diagram_size=config.diagram_size,
            page_size=config.page_size,
        )
    except UseCaseError as exc:
        err(str(exc))
        return
    except ValueError as exc:
        err(str(exc))
        return
    print(f"Rendered: {output_path}")


def cmd_upload(tokens: list[str]) -> None:
    game_id = tokens[0] if tokens else _require_open_session()
    if game_id is None:
        err("Usage: upload <game-id>")
        return
    try:
        url = get_service().upload_to_lichess(game_id=game_id)
    except UseCaseError as exc:
        err(str(exc))
        return
    print(url)


def cmd_see(tokens: list[str]) -> None:
    game_id = tokens[0] if tokens else _require_open_session()
    if game_id is None:
        err("Usage: see <game-id>")
        return
    try:
        url = get_service().upload_to_lichess(game_id=game_id)
    except UseCaseError as exc:
        err(str(exc))
        return
    webbrowser.open(url)
    print(url)


def cmd_copy(tokens: list[str]) -> None:
    if _session.open:
        if not tokens:
            err("Usage: copy <new-game-id>")
            return
        source_game_id = _session.game_id
        new_game_id = tokens[0]
    else:
        if len(tokens) != 2:
            err("Usage: copy <source-game-id> <new-game-id>")
            return
        source_game_id, new_game_id = tokens
    try:
        get_service().save_game_as(
            source_game_id=source_game_id,
            new_game_id=new_game_id,
        )
    except OverwriteRequiredError:
        answer = input(f"Game id '{new_game_id}' exists. Overwrite? (yes/no): ").strip().lower()
        if answer != "yes":
            print("Copy cancelled.")
            return
        get_service().save_game_as(
            source_game_id=source_game_id,
            new_game_id=new_game_id,
            overwrite=True,
        )
    except UseCaseError as exc:
        err(str(exc))
        return
    print(f"Created: {new_game_id}")


def cmd_delete(tokens: list[str]) -> None:
    game_id = tokens[0] if tokens else _require_open_session()
    if game_id is None:
        err("Usage: delete <game-id>")
        return
    answer = input(f"Delete '{game_id}'? (yes/no): ").strip().lower()
    if answer != "yes":
        print("Delete cancelled.")
        return
    try:
        get_service().delete_game(game_id)
    except UseCaseError as exc:
        err(str(exc))
        return
    if _session.game_id == game_id:
        _session.game_id = None
        _session.current_turning_point_ply = None
    print(f"Deleted: {game_id}")


def cmd_json(_tokens: list[str]) -> None:
    game_id = _require_open_session()
    if game_id is None:
        return
    repo = get_repo()
    try:
        annotation = repo.load_working_copy(game_id)
    except FileNotFoundError:
        err(f"Session is not open for game: {game_id}")
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
    print(json.dumps(payload, indent=2))


def cmd_quit(_tokens: list[str]) -> None:
    if _session.open:
        if not _do_close():
            return
    sys.exit(0)


_HELP_NO_SESSION = """\
Commands (no session open):
  import                    Import a game from a PGN file and open it
  new                       Alias for import
  open <game-id>            Open or resume a game
  list                      List games in the store
  copy <source> <new>       Save game as a new game id
  delete <game-id>          Delete a game
  render <game-id>          Render a game to output.pdf
  upload <game-id>          Upload a game to Lichess and print the URL
  see <game-id>             Upload a game to Lichess and open the URL
  help                      Show this help
  quit                      Exit"""

_HELP_SESSION = """\
Commands (session open):
  segments                  List segments for the open game
  view <segment-number>     View one segment and select it
  split <move> [label]      Add a turning point
  merge <move>              Remove a turning point
  label <text>              Set the current segment label
  comment                   Edit the current segment annotation in $EDITOR
  diagram [on|off]          Toggle or set the current segment diagram flag
  save                      Save the open game
  close                     Close the current game
  copy <new-game-id>        Save the current game as a new game id
  delete [game-id]          Delete the current game or a named one
  render [game-id]          Render the current or named game to output.pdf
  upload [game-id]          Upload the current or named game to Lichess
  see [game-id]             Upload to Lichess and open the URL
  json                      Print the working annotation JSON summary
  help                      Show this help
  quit                      Close the current game and exit"""


def cmd_help(_tokens: list[str]) -> None:
    print(_HELP_SESSION if _session.open else _HELP_NO_SESSION)


_COMMANDS_NO_SESSION = {
    "import": cmd_import,
    "new": cmd_new,
    "open": cmd_open,
    "list": cmd_list,
    "copy": cmd_copy,
    "delete": cmd_delete,
    "render": cmd_render,
    "upload": cmd_upload,
    "see": cmd_see,
    "help": cmd_help,
    "quit": cmd_quit,
}

_COMMANDS_SESSION = {
    "segments": cmd_segments,
    "view": cmd_view,
    "split": cmd_split,
    "merge": cmd_merge,
    "label": cmd_label,
    "comment": cmd_comment,
    "diagram": cmd_diagram,
    "save": cmd_save,
    "close": cmd_close,
    "copy": cmd_copy,
    "delete": cmd_delete,
    "render": cmd_render,
    "upload": cmd_upload,
    "see": cmd_see,
    "json": cmd_json,
    "help": cmd_help,
    "quit": cmd_quit,
}


def check_stale_working_copies() -> None:
    repo = get_repo()
    stale = repo.stale_working_copies()
    if not stale:
        return
    for game_id in stale:
        try:
            annotation = repo.load_working_copy(game_id)
        except Exception:
            repo.discard_working_copy(game_id)
            continue
        print(f"Working copy found for '{annotation.title}' ({game_id}).")
        answer = input("Resume? (yes/no): ").strip().lower()
        if answer == "yes":
            _open_game(game_id)
            return
        repo.discard_working_copy(game_id)
        print("Discarded.")


def main() -> None:
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
            continue

        if not line:
            continue

        parts = line.split(None, 1)
        cmd_name = parts[0].lower()
        tokens = parts[1].split() if len(parts) > 1 else []

        table = _COMMANDS_SESSION if _session.open else _COMMANDS_NO_SESSION
        handler = table.get(cmd_name)
        if handler is None:
            print(f"Unknown command: {cmd_name!r}. Type 'help' for a list.")
            continue
        handler(tokens)
