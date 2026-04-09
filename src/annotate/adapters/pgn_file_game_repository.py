import io
import json
import shutil
from pathlib import Path

import chess.pgn

from annotate.domain.annotation import Annotation
from annotate.domain.segment import SegmentContent
from annotate.ports import GameRepository

# The comment string embedded in PGN move comments to mark turning points.
TP_MARKER = "[%tp]"


def strip_comments_and_nags(pgn_text: str) -> str:
    """Return a copy of ``pgn_text`` with all comments and NAGs removed from the main line.

    Called at import time to give the system a clean baseline PGN free of any
    third-party annotations. Raises ``ValueError`` if the PGN cannot be parsed.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Could not parse PGN")

    # Strip comments and NAGs from every node in the main line.
    for node in game.mainline():
        node.comment = ""
        node.starting_comment = ""
        node.nags.clear()

    exporter = chess.pgn.StringExporter(
        headers=True,
        variations=True,
        comments=False,
    )
    return game.accept(exporter)


def _annotation_json_data(annotation: Annotation) -> dict:
    """Serialise ``annotation`` to the dict structure used in ``annotation.json``.

    The returned dict has two top-level keys:
    * ``"game"``     — top-level metadata (title, author, date, sides).
    * ``"segments"`` — per-segment content keyed by ply string, sorted by ply.
    """
    return {
        "game": {
            "title": annotation.title,
            "author": annotation.author,
            "date": annotation.date,
            "player_side": annotation.player_side,
            "diagram_orientation": annotation.diagram_orientation,
        },
        "segments": {
            str(ply): {
                "label": content.label,
                "annotation": content.annotation,
                "show_diagram": content.show_diagram,
            }
            for ply, content in sorted(annotation.segment_contents.items())
        },
    }


def _annotation_from_json_and_pgn(
    *,
    game_id: str,
    pgn_text: str,
    json_data: dict,
) -> Annotation:
    """Reconstruct an ``Annotation`` from a PGN string and a parsed ``annotation.json`` dict.

    Handles the legacy ``"commentary"`` key as a fallback for the ``"annotation"``
    field so that games written by older versions of the tool can still be loaded.
    """
    game_data = json_data.get("game", {})
    # Build SegmentContent for each segment, supporting the old "commentary" key name.
    segment_contents = {
        int(ply): SegmentContent(
            label=data.get("label", ""),
            annotation=data.get("annotation", data.get("commentary", "")),
            show_diagram=data.get("show_diagram", True),
        )
        for ply, data in json_data["segments"].items()
    }
    # Derive the turning-point list from the segment keys.
    turning_points = sorted(segment_contents)
    return Annotation(
        game_id=game_id,
        title=game_data.get("title", ""),
        author=game_data.get("author", ""),
        date=game_data.get("date", ""),
        pgn=pgn_text,
        player_side=game_data.get("player_side", "white"),
        diagram_orientation=game_data.get("diagram_orientation", "white"),
        turning_points=turning_points,
        segment_contents=segment_contents,
    )


def _load_game(pgn_text: str):
    """Parse ``pgn_text`` with python-chess and return the game object.

    Raises ``ValueError`` if the PGN cannot be parsed.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Could not parse PGN")
    return game


def turning_points_from_pgn(pgn_text: str) -> list[int]:
    """Extract the sorted list of turning-point plies from ``[%tp]`` markers in PGN comments.

    Validates that:
    * At least one marker is present.
    * The first marker is at ply 1.
    * There are no duplicate markers.

    Raises ``ValueError`` for any of the above violations.
    """
    game = _load_game(pgn_text)
    turning_points: list[int] = []
    for ply, node in enumerate(game.mainline(), start=0):
        # Ply 0 is the starting position (before any moves); skip it.
        if ply == 0:
            continue
        if TP_MARKER in node.comment:
            turning_points.append(ply)
    if not turning_points:
        raise ValueError("Annotated PGN must contain a turning point at ply 1")
    if turning_points[0] != 1:
        raise ValueError("The first turning point in PGN must be ply 1")
    if len(set(turning_points)) != len(turning_points):
        raise ValueError("Annotated PGN contains duplicate turning-point markers")
    return turning_points


def pgn_with_turning_points(annotation: Annotation) -> str:
    """Return a PGN string with ``{ [%tp] }`` comments inserted at each turning-point ply.

    All other comments and NAGs are cleared so the only comments in the output
    are the turning-point markers. The resulting string is suitable for writing
    to ``annotated.pgn`` or its working-copy equivalent.
    """
    game = _load_game(annotation.pgn)
    for ply, node in enumerate(game.mainline(), start=0):
        if ply == 0:
            continue
        # Set the marker comment at turning points; clear it everywhere else.
        node.comment = TP_MARKER if ply in annotation.turning_points else ""
        node.starting_comment = ""
        node.nags.clear()
    exporter = chess.pgn.StringExporter(
        headers=True,
        variations=True,
        comments=True,  # must be True so [%tp] markers are preserved
    )
    return game.accept(exporter)


def validate_pgn_json_sync(pgn_text: str, json_data: dict) -> None:
    """Assert that the PGN turning-point markers and JSON segment keys are identical.

    Raises ``ValueError`` if the two collections differ, indicating that the
    on-disk files are out of sync.
    """
    pgn_turning_points = turning_points_from_pgn(pgn_text)
    json_turning_points = sorted(int(ply) for ply in json_data["segments"])
    if pgn_turning_points != json_turning_points:
        raise ValueError(
            "Turning points in annotated PGN do not match annotation.json segment keys"
        )


def _read_json_file(path: Path) -> dict:
    """Read and parse a JSON file, raising ``ValueError`` on parse failure."""
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse JSON file: {path}") from exc


def _load_annotation_state(*, game_id: str, pgn_path: Path, json_path: Path) -> Annotation:
    """Read both files for a game, validate their consistency, and reconstruct the Annotation.

    Raises ``ValueError`` if either file cannot be read, if they are inconsistent,
    or if the data cannot be deserialised into an ``Annotation``.
    """
    try:
        pgn_text = pgn_path.read_text()
    except OSError as exc:
        raise ValueError(f"Could not read PGN file: {pgn_path}") from exc

    json_data = _read_json_file(json_path)
    # Ensure the turning-point markers in the PGN match the segment keys in the JSON.
    try:
        validate_pgn_json_sync(pgn_text, json_data)
    except ValueError as exc:
        raise ValueError(f"Corrupted stored game '{game_id}': {exc}") from exc

    try:
        return _annotation_from_json_and_pgn(
            game_id=str(game_id),
            pgn_text=pgn_text,
            json_data=json_data,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Corrupted annotation data for game '{game_id}'") from exc


class PGNFileGameRepository(GameRepository):
    """Persist each annotated game in its own subdirectory under a root store directory.

    Each game directory contains two canonical files:

    * ``annotated.pgn``   — the cleaned PGN with ``{ [%tp] }`` comments at each
      turning-point ply and no other comments or NAGs.
    * ``annotation.json`` — segment labels, annotation text, and ``show_diagram``
      flags keyed by ply string, plus top-level game metadata.

    While a session is open two additional working-copy files are maintained:

    * ``annotated.pgn.work``
    * ``annotation.json.work``

    These mirror the canonical files but accumulate unsaved edits. A session is
    considered in-progress simply by the presence of these files. If the process
    exits unexpectedly the working files persist and are offered for resumption on
    the next startup.

    The repository validates that the ``[%tp]`` ply markers in the PGN exactly
    match the segment keys in the JSON on every read and write.
    """

    # File name constants, kept here so they can be referenced by tests.
    MAIN_PGN = "annotated.pgn"
    MAIN_JSON = "annotation.json"
    WORK_PGN = "annotated.pgn.work"
    WORK_JSON = "annotation.json.work"
    OUTPUT_PDF = "output.pdf"

    def __init__(self, store_dir: Path) -> None:
        """Initialise the repository, creating the store directory if it does not exist."""
        self._store = Path(store_dir)
        self._store.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Path helpers                                                         #
    # ------------------------------------------------------------------ #

    def game_dir(self, game_id: str | int) -> Path:
        """Return the directory path for ``game_id``."""
        return self._store / str(game_id)

    def main_pgn_path(self, game_id: str | int) -> Path:
        """Return the canonical PGN file path for ``game_id``."""
        return self.game_dir(game_id) / self.MAIN_PGN

    def main_json_path(self, game_id: str | int) -> Path:
        """Return the canonical JSON file path for ``game_id``."""
        return self.game_dir(game_id) / self.MAIN_JSON

    def work_pgn_path(self, game_id: str | int) -> Path:
        """Return the working-copy PGN file path for ``game_id``."""
        return self.game_dir(game_id) / self.WORK_PGN

    def work_json_path(self, game_id: str | int) -> Path:
        """Return the working-copy JSON file path for ``game_id``."""
        return self.game_dir(game_id) / self.WORK_JSON

    def output_pdf_path(self, game_id: str | int) -> Path:
        """Return the output PDF file path for ``game_id``."""
        return self.game_dir(game_id) / self.OUTPUT_PDF

    # ------------------------------------------------------------------ #
    # GameRepository interface                                             #
    # ------------------------------------------------------------------ #

    def save(self, annotation: Annotation) -> None:
        """Serialise ``annotation`` to the canonical PGN and JSON files.

        The game directory is created if it does not already exist. Both files
        are validated for consistency before writing.
        """
        game_dir = self.game_dir(annotation.game_id)
        game_dir.mkdir(parents=True, exist_ok=True)
        pgn_text = pgn_with_turning_points(annotation)
        json_data = _annotation_json_data(annotation)
        # Verify consistency before touching the filesystem.
        validate_pgn_json_sync(pgn_text, json_data)
        self.main_pgn_path(annotation.game_id).write_text(pgn_text)
        self.main_json_path(annotation.game_id).write_text(
            json.dumps(json_data, indent=2, sort_keys=True)
        )

    def exists(self, game_id: str | int) -> bool:
        """Return True when both canonical files exist for ``game_id``."""
        game_dir = self.game_dir(game_id)
        return game_dir.is_dir() and self.main_pgn_path(game_id).exists() and self.main_json_path(game_id).exists()

    def load(self, game_id: str | int) -> Annotation:
        """Load and return the canonical ``Annotation`` for ``game_id``.

        Raises ``FileNotFoundError`` if either canonical file is missing.
        """
        pgn_path = self.main_pgn_path(game_id)
        json_path = self.main_json_path(game_id)
        if not pgn_path.exists() or not json_path.exists():
            raise FileNotFoundError(f"No game found: {game_id}")
        return _load_annotation_state(
            game_id=str(game_id),
            pgn_path=pgn_path,
            json_path=json_path,
        )

    def list_all(self) -> list[tuple[str, str]]:
        """Return ``(game_id, title)`` pairs for every valid canonical game, sorted by game id.

        Subdirectories that lack both canonical files, or whose JSON cannot be
        parsed, are silently skipped.
        """
        result: list[tuple[str, str]] = []
        for path in sorted(self._store.iterdir()):
            if not path.is_dir():
                continue
            pgn_path = path / self.MAIN_PGN
            json_path = path / self.MAIN_JSON
            if not pgn_path.exists() or not json_path.exists():
                continue
            try:
                json_data = _read_json_file(json_path)
            except ValueError:
                # Skip directories whose JSON is unreadable.
                continue
            title = json_data.get("game", {}).get("title", "")
            result.append((path.name, title))
        return result

    def exists_working_copy(self, game_id: str | int) -> bool:
        """Return True when at least one working-copy file exists for ``game_id``."""
        work_pgn = self.work_pgn_path(game_id)
        work_json = self.work_json_path(game_id)
        return work_pgn.exists() or work_json.exists()

    def save_working_copy(self, annotation: Annotation) -> None:
        """Write ``annotation`` to the working-copy files.

        The game directory is created if it does not already exist. Both files
        are validated for consistency before writing.
        """
        game_dir = self.game_dir(annotation.game_id)
        game_dir.mkdir(parents=True, exist_ok=True)
        pgn_text = pgn_with_turning_points(annotation)
        json_data = _annotation_json_data(annotation)
        validate_pgn_json_sync(pgn_text, json_data)
        self.work_pgn_path(annotation.game_id).write_text(pgn_text)
        self.work_json_path(annotation.game_id).write_text(
            json.dumps(json_data, indent=2, sort_keys=True)
        )

    def load_working_copy(self, game_id: str | int) -> Annotation:
        """Load and return the working-copy ``Annotation`` for ``game_id``.

        Raises ``FileNotFoundError`` if either working-copy file is missing.
        """
        pgn_path = self.work_pgn_path(game_id)
        json_path = self.work_json_path(game_id)
        if not pgn_path.exists() or not json_path.exists():
            raise FileNotFoundError(f"No working copy found: {game_id}")
        return _load_annotation_state(
            game_id=str(game_id),
            pgn_path=pgn_path,
            json_path=json_path,
        )

    def discard_working_copy(self, game_id: str | int) -> None:
        """Delete both working-copy files for ``game_id``, if they exist."""
        for path in (self.work_pgn_path(game_id), self.work_json_path(game_id)):
            if path.exists():
                path.unlink()

    def commit_working_copy(self, game_id: str | int) -> None:
        """Overwrite the canonical files with the working-copy files.

        The working-copy files are left in place after the commit. Raises
        ``FileNotFoundError`` if either working-copy file is missing.
        """
        work_pgn = self.work_pgn_path(game_id)
        work_json = self.work_json_path(game_id)
        if not work_pgn.exists() or not work_json.exists():
            raise FileNotFoundError(f"No working copy to commit: {game_id}")
        shutil.copy2(work_pgn, self.main_pgn_path(game_id))
        shutil.copy2(work_json, self.main_json_path(game_id))

    def has_unsaved_working_copy(self, game_id: str | int) -> bool:
        """Return True when the working-copy files differ from the canonical files.

        Returns False when no working-copy files exist. Returns True when
        working-copy files exist but canonical files do not (i.e. a newly
        imported game that has never been committed).
        """
        work_pgn = self.work_pgn_path(game_id)
        work_json = self.work_json_path(game_id)
        main_pgn = self.main_pgn_path(game_id)
        main_json = self.main_json_path(game_id)
        if not work_pgn.exists() or not work_json.exists():
            # No working copy at all — nothing is unsaved.
            return False
        if not main_pgn.exists() or not main_json.exists():
            # Working copy exists but canonical files don't — treat as unsaved.
            return True
        # Compare file contents directly; if either differs, changes are unsaved.
        return (
            work_pgn.read_text() != main_pgn.read_text()
            or work_json.read_text() != main_json.read_text()
        )

    def stale_working_copies(self) -> list[str]:
        """Return the game ids of all games that currently have working-copy files.

        Used at startup to find sessions that were interrupted before the user
        closed them cleanly.
        """
        result: list[str] = []
        for path in sorted(self._store.iterdir()):
            if not path.is_dir():
                continue
            # A game has a stale session if either working-copy file is present.
            if (path / self.WORK_PGN).exists() or (path / self.WORK_JSON).exists():
                result.append(path.name)
        return result

    def delete(self, game_id: str | int) -> None:
        """Permanently remove the game directory and all files within it.

        Raises ``FileNotFoundError`` if the game directory does not exist.
        """
        game_dir = self.game_dir(game_id)
        if not game_dir.exists():
            raise FileNotFoundError(f"No game found: {game_id}")
        shutil.rmtree(game_dir)

    def next_id(self) -> int:
        """Return the next available integer game id for backward compatibility.

        Scans the store for directories whose names are valid integers and
        returns one greater than the current maximum. Returns 1 when the store
        is empty or contains no integer-named directories.
        """
        max_id = 0
        for path in self._store.iterdir():
            if not path.is_dir():
                continue
            try:
                max_id = max(max_id, int(path.name))
            except ValueError:
                # Skip directories with non-integer names.
                pass
        return max_id + 1


# Backward-compatible adapter name retained while CLI modules migrate.
JSONFileAnnotationRepository = PGNFileGameRepository
