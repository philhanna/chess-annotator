import io
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import chess.pgn

from annotate.adapters.pgn_file_game_repository import strip_comments_and_nags
from annotate.domain.annotation import Annotation
from annotate.domain.model import (
    derive_segments,
    find_segment_by_turning_point,
    format_move_list,
    game_headers,
    san_move_range,
)
from annotate.domain.segment import SegmentView
from annotate.ports import DocumentRenderer, GameRepository, LichessUploader, PGNParser
from annotate.use_cases.interactors import merge_segment, merge_segments_by_index, split_segment


# ---------------------------------------------------------------------------
# Application-layer exceptions
# ---------------------------------------------------------------------------

class UseCaseError(Exception):
    """Base class for all application-layer errors raised by use-case methods."""


class GameNotFoundError(UseCaseError):
    """Raised when a requested game id does not exist in the store."""


class SessionNotOpenError(UseCaseError):
    """Raised when a use-case method requires an open session but none exists."""


class SegmentNotFoundError(UseCaseError):
    """Raised when a requested turning-point ply does not correspond to any segment."""


class OverwriteRequiredError(UseCaseError):
    """Raised when a target game id already exists and the caller did not set ``overwrite=True``."""


class MissingDependencyError(UseCaseError):
    """Raised when a use-case method requires an optional adapter that was not supplied."""


# ---------------------------------------------------------------------------
# Read-model data transfer objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SegmentSummary:
    """Lightweight summary of one segment, used by the list and navigation commands.

    ``has_annotation`` is True when the segment's annotation text is non-blank.
    ``move_range`` is a human-readable span such as ``"1. e4 to 5...Nf6"``.
    """

    turning_point_ply: int
    start_ply: int
    end_ply: int
    move_range: str
    label: str
    has_annotation: bool
    show_diagram: bool


@dataclass(frozen=True)
class SegmentDetail:
    """Full detail view of one segment, used by the ``view`` and ``edit`` commands.

    ``move_list`` is the complete SAN move sequence for the segment's ply range.
    ``diagram_path`` is set when ``show_diagram`` is True and a diagram renderer
    is configured; it points to a cached SVG file in the game's preview directory.
    """

    turning_point_ply: int
    start_ply: int
    end_ply: int
    move_range: str
    label: str
    annotation: str
    move_list: str
    show_diagram: bool
    diagram_path: Path | None


@dataclass(frozen=True)
class GameSummary:
    """Summary of one stored game, as shown by the ``list`` command.

    ``in_progress`` is True when working-copy files exist for the game, indicating
    that a session was opened and has not yet been closed.
    """

    game_id: str
    title: str
    white: str
    black: str
    event: str
    date: str
    result: str
    in_progress: bool


@dataclass(frozen=True)
class GameState:
    """Snapshot of a game's open session, returned by open/save/import operations.

    ``resumed`` is True when ``open_game`` found an existing working copy rather
    than creating a fresh one. ``has_unsaved_changes`` reflects whether the working
    copy currently differs from the canonical files.
    """

    game_id: str
    title: str
    session_open: bool
    has_unsaved_changes: bool
    segments: list[SegmentSummary]
    resumed: bool = False


@dataclass(frozen=True)
class CloseGameResult:
    """Result of a ``close_game`` call, which may require a second round-trip.

    When ``requires_confirmation`` is True the session was not closed; the caller
    must ask the user whether to save or discard and then call ``close_game`` again
    with an explicit ``save_changes`` value. ``saved`` and ``discarded`` are set on
    the final call to indicate which action was taken.
    """

    game_id: str
    closed: bool
    requires_confirmation: bool
    saved: bool = False
    discarded: bool = False


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _segment_summary(segment: SegmentView, pgn: str) -> SegmentSummary:
    """Build a ``SegmentSummary`` from a derived ``SegmentView`` and its game PGN."""
    return SegmentSummary(
        turning_point_ply=segment.turning_point_ply,
        start_ply=segment.start_ply,
        end_ply=segment.end_ply,
        move_range=san_move_range(pgn, segment.start_ply, segment.end_ply),
        label=segment.label,
        has_annotation=bool(segment.annotation.strip()),
        show_diagram=segment.show_diagram,
    )


def _game_state(
    repo: GameRepository,
    annotation: Annotation,
    *,
    session_open: bool,
    resumed: bool = False,
) -> GameState:
    """Build a ``GameState`` snapshot from the current repository and annotation."""
    return GameState(
        game_id=annotation.game_id,
        title=annotation.title,
        session_open=session_open,
        has_unsaved_changes=repo.has_unsaved_working_copy(annotation.game_id),
        segments=[_segment_summary(segment, annotation.pgn) for segment in derive_segments(annotation)],
        resumed=resumed,
    )


def _select_game_text(pgn_text: str, game_index: int) -> str:
    """Extract the PGN text of the game at ``game_index`` (0-based) from a multi-game file.

    Raises ``ValueError`` if the PGN cannot be parsed, contains no games, or
    ``game_index`` is out of range.
    """
    games = []
    stream = io.StringIO(pgn_text)
    # Read all games from the stream before indexing.
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        games.append(game)
    if not games:
        raise ValueError("Could not parse PGN: no game found")
    if not (0 <= game_index < len(games)):
        raise ValueError(f"PGN game index {game_index} is out of range")
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    return games[game_index].accept(exporter)


# ---------------------------------------------------------------------------
# Application service
# ---------------------------------------------------------------------------

class AnnotationService:
    """Coordinate all annotation use cases against the injected port adapters.

    This is the single application-layer class. Every public method maps to one
    use case. All ports are supplied at construction time; optional ports
    (``document_renderer``, ``lichess_uploader``, ``diagram_renderer``) raise
    ``MissingDependencyError`` when a use case that requires them is invoked
    without them.
    """

    def __init__(
        self,
        *,
        repository: GameRepository,
        pgn_parser: PGNParser,
        store_dir: Path,
        document_renderer: DocumentRenderer | None = None,
        lichess_uploader: LichessUploader | None = None,
        diagram_renderer=None,
    ) -> None:
        """Initialise the service with the required and optional port adapters.

        Args:
            repository:        The game repository adapter (required).
            pgn_parser:        The PGN parser adapter (required).
            store_dir:         Root store directory for PDF output and diagram caches.
            document_renderer: Optional renderer for producing PDF documents.
            lichess_uploader:  Optional adapter for uploading games to Lichess.
            diagram_renderer:  Optional adapter for rendering board diagram previews.
        """
        self.repository = repository
        self.pgn_parser = pgn_parser
        self.store_dir = Path(store_dir)
        self.document_renderer = document_renderer
        self.lichess_uploader = lichess_uploader
        self.diagram_renderer = diagram_renderer

    def import_game(
        self,
        *,
        game_id: str,
        pgn_text: str,
        player_side: str,
        author: str = "",
        date: str | None = None,
        diagram_orientation: str | None = None,
        overwrite: bool = False,
        game_index: int = 0,
    ) -> GameState:
        """Import a PGN string as a new annotated game and immediately open a session.

        Strips all existing comments and NAGs from the PGN; the cleaned copy becomes
        the canonical PGN. Creates a single initial segment starting at ply 1. When
        ``pgn_text`` contains multiple games, ``game_index`` (0-based) selects which
        one to import.

        Args:
            game_id:             Unique identifier for the new game.
            pgn_text:            Raw PGN string (may contain multiple games).
            player_side:         ``"white"`` or ``"black"`` — the annotated player.
            author:              Author name for the annotation document.
            date:                Override for the annotation date; defaults to the PGN Date header.
            diagram_orientation: Board orientation for diagrams; defaults to ``player_side``.
            overwrite:           If True, delete any existing game with the same id first.
            game_index:          0-based index of the game to import from a multi-game file.

        Raises:
            OverwriteRequiredError: if ``game_id`` already exists and ``overwrite`` is False.
        """
        if self.repository.exists(game_id) and not overwrite:
            raise OverwriteRequiredError(f"Game id already exists: {game_id}")
        if self.repository.exists(game_id):
            # Delete the existing game before overwriting.
            self.repository.delete(game_id)

        # Extract the target game from a potentially multi-game PGN file.
        selected_game = _select_game_text(pgn_text, game_index)
        cleaned_pgn = strip_comments_and_nags(selected_game)
        info = self.pgn_parser.parse(cleaned_pgn)

        # Build a human-readable title from the player names and date.
        white = info["white"] if info["white"] != "?" else "N/A"
        black = info["black"] if info["black"] != "?" else "N/A"
        raw_date = info["date"].replace("?", "").strip(".") or "N/A"
        title = f"{white} - {black} {raw_date}"

        annotation = Annotation.create(
            game_id=game_id,
            title=title,
            author=author,
            date=date or (info["date"].replace("?", "").strip(".") or ""),
            pgn=cleaned_pgn,
            player_side=player_side,
            diagram_orientation=diagram_orientation,
        )
        # Save both the canonical copy and a working copy to open the session.
        self.repository.save(annotation)
        self.repository.save_working_copy(annotation)
        return _game_state(self.repository, annotation, session_open=True)

    def list_games(self) -> list[GameSummary]:
        """Return a ``GameSummary`` for every stored game, sorted alphabetically by game id."""
        result: list[GameSummary] = []
        for game_id, title in self.repository.list_all():
            annotation = self.repository.load(game_id)
            headers = game_headers(annotation.pgn)
            result.append(
                GameSummary(
                    game_id=game_id,
                    title=title,
                    white=headers.get("White", "?"),
                    black=headers.get("Black", "?"),
                    event=headers.get("Event", "?"),
                    date=headers.get("Date", "?"),
                    result=headers.get("Result", "?"),
                    in_progress=self.repository.exists_working_copy(game_id),
                )
            )
        return result

    def open_game(self, game_id: str) -> GameState:
        """Open a game for editing, resuming an in-progress session if one exists.

        If working-copy files are already present for ``game_id``, they are loaded
        and ``GameState.resumed`` is set to True. Otherwise a fresh working copy is
        created from the canonical files.

        Raises:
            GameNotFoundError: if ``game_id`` is not in the store.
        """
        if not self.repository.exists(game_id):
            raise GameNotFoundError(f"Game not found: {game_id}")
        if self.repository.exists_working_copy(game_id):
            # Resume the interrupted session rather than starting fresh.
            annotation = self.repository.load_working_copy(game_id)
            return _game_state(
                self.repository,
                annotation,
                session_open=True,
                resumed=True,
            )
        # No working copy — create one from the canonical files.
        annotation = self.repository.load(game_id)
        self.repository.save_working_copy(annotation)
        return _game_state(self.repository, annotation, session_open=True, resumed=False)

    def save_game_as(
        self,
        *,
        source_game_id: str,
        new_game_id: str,
        overwrite: bool = False,
    ) -> None:
        """Copy a game under a new id without opening a session on the copy.

        If the source game has an open working copy, that copy is used so that
        any in-progress edits are captured in the duplicate. The new game is
        written to the canonical store only; no working files are created for it.

        Raises:
            GameNotFoundError:    if ``source_game_id`` is not in the store.
            OverwriteRequiredError: if ``new_game_id`` already exists and ``overwrite`` is False.
        """
        if not self.repository.exists(source_game_id):
            raise GameNotFoundError(f"Game not found: {source_game_id}")
        if self.repository.exists(new_game_id):
            if not overwrite:
                raise OverwriteRequiredError(f"Game id already exists: {new_game_id}")
            self.repository.delete(new_game_id)

        # Prefer the working copy so in-progress edits are included in the duplicate.
        if self.repository.exists_working_copy(source_game_id):
            annotation = self.repository.load_working_copy(source_game_id)
        else:
            annotation = self.repository.load(source_game_id)
        annotation.game_id = new_game_id
        annotation.annotation_id = new_game_id
        self.repository.save(annotation)

    def delete_game(self, game_id: str) -> None:
        """Permanently delete a game and all its associated files from the store.

        Raises:
            GameNotFoundError: if ``game_id`` is not in the store.
        """
        if not self.repository.exists(game_id):
            raise GameNotFoundError(f"Game not found: {game_id}")
        self.repository.delete(game_id)

    def add_turning_point(
        self, *, game_id: str, ply: int, label: str = ""
    ) -> list[SegmentSummary]:
        """Split the segment that contains ``ply`` by inserting a new turning point.

        The new segment starts at ``ply`` and receives ``label`` as its initial
        label with empty annotation text. Saves the working copy after the split.

        Raises:
            SessionNotOpenError: if no working copy exists for ``game_id``.
            ValueError:          if ``ply`` is out of range or already a turning point.
        """
        annotation = self._load_session(game_id)
        updated = split_segment(annotation, ply, label)
        self.repository.save_working_copy(updated)
        return [_segment_summary(segment, updated.pgn) for segment in derive_segments(updated)]

    def remove_turning_point(
        self, *, game_id: str, ply: int, force: bool = False
    ) -> list[SegmentSummary]:
        """Remove the turning point at ``ply``, merging it into the preceding segment.

        The segment's label and annotation are discarded. If the segment has any
        authored content and ``force`` is False, raises ``UseCaseError`` rather than
        silently discarding the content. Saves the working copy after the merge.

        Raises:
            SessionNotOpenError: if no working copy exists for ``game_id``.
            UseCaseError:        if the segment has content and ``force`` is False.
            ValueError:          if ``ply`` is not a turning point, or is ply 1.
        """
        annotation = self._load_session(game_id)
        updated, merged = merge_segment(annotation, ply, force=force)
        if not merged:
            raise UseCaseError("Turning point has content; force is required to remove it")
        self.repository.save_working_copy(updated)
        return [_segment_summary(segment, updated.pgn) for segment in derive_segments(updated)]

    def merge_segments(
        self, *, game_id: str, m: int, n: int
    ) -> list[SegmentSummary]:
        """Collapse segments ``m`` through ``n`` (1-based) into one, concatenating their content.

        Labels are space-joined; annotation texts are blank-line-joined. Saves the
        working copy after the merge.

        Raises:
            SessionNotOpenError: if no working copy exists for ``game_id``.
            UseCaseError:        if ``m`` or ``n`` are out of range or ``m >= n``.
        """
        annotation = self._load_session(game_id)
        total = len(annotation.turning_points)
        if not (1 <= m < n <= total):
            raise UseCaseError(
                f"Segment indices must satisfy 1 <= m < n <= {total}; got m={m}, n={n}"
            )
        updated = merge_segments_by_index(annotation, m, n)
        self.repository.save_working_copy(updated)
        return [_segment_summary(segment, updated.pgn) for segment in derive_segments(updated)]

    def set_segment_label(
        self, *, game_id: str, turning_point_ply: int, label: str
    ) -> SegmentDetail:
        """Set the label for the segment at ``turning_point_ply`` and save the working copy.

        Raises:
            SessionNotOpenError:  if no working copy exists for ``game_id``.
            UseCaseError:         if ``label`` is blank.
            SegmentNotFoundError: if ``turning_point_ply`` is not a turning point.
        """
        if not label.strip():
            raise UseCaseError("label must not be blank")
        annotation = self._load_session(game_id)
        content = self._segment_content(annotation, turning_point_ply)
        content.label = label
        self.repository.save_working_copy(annotation)
        return self._segment_detail(annotation, turning_point_ply)

    def set_segment_annotation(
        self, *, game_id: str, turning_point_ply: int, annotation_text: str
    ) -> SegmentDetail:
        """Set the annotation text for the segment at ``turning_point_ply`` and save the working copy.

        Raises:
            SessionNotOpenError:  if no working copy exists for ``game_id``.
            UseCaseError:         if ``annotation_text`` is blank.
            SegmentNotFoundError: if ``turning_point_ply`` is not a turning point.
        """
        if not annotation_text.strip():
            raise UseCaseError("annotation must not be blank")
        annotation = self._load_session(game_id)
        content = self._segment_content(annotation, turning_point_ply)
        content.annotation = annotation_text
        self.repository.save_working_copy(annotation)
        return self._segment_detail(annotation, turning_point_ply)

    def toggle_segment_diagram(
        self, *, game_id: str, turning_point_ply: int
    ) -> SegmentDetail:
        """Toggle the ``show_diagram`` flag for the segment at ``turning_point_ply`` and save the working copy.

        Raises:
            SessionNotOpenError:  if no working copy exists for ``game_id``.
            SegmentNotFoundError: if ``turning_point_ply`` is not a turning point.
        """
        annotation = self._load_session(game_id)
        content = self._segment_content(annotation, turning_point_ply)
        content.show_diagram = not content.show_diagram
        self.repository.save_working_copy(annotation)
        return self._segment_detail(annotation, turning_point_ply)

    def save_session(self, game_id: str) -> GameState:
        """Commit the working copy to the canonical files while keeping the session open.

        Raises:
            SessionNotOpenError: if no working copy exists for ``game_id``.
        """
        annotation = self._load_session(game_id)
        # Re-save the working copy to ensure it is up to date, then commit.
        self.repository.save_working_copy(annotation)
        self.repository.commit_working_copy(game_id)
        return _game_state(self.repository, self.repository.load_working_copy(game_id), session_open=True)

    def close_game(
        self, game_id: str, save_changes: bool | None = None
    ) -> CloseGameResult:
        """Close the open session, optionally saving or discarding unsaved changes.

        When ``save_changes`` is None and the working copy differs from the canonical
        files, returns a ``CloseGameResult`` with ``requires_confirmation=True`` without
        actually closing. The caller should then prompt the user and call ``close_game``
        again with ``save_changes=True`` (to commit) or ``save_changes=False`` (to discard).

        If there are no unsaved changes the session is closed regardless of ``save_changes``.

        Raises:
            SessionNotOpenError: if no working copy exists for ``game_id``.
        """
        self._load_session(game_id)
        has_unsaved = self.repository.has_unsaved_working_copy(game_id)
        if not has_unsaved:
            # Nothing to save — clean close.
            self.repository.discard_working_copy(game_id)
            return CloseGameResult(game_id=game_id, closed=True, requires_confirmation=False)
        if save_changes is None:
            # Caller needs to ask the user what to do.
            return CloseGameResult(game_id=game_id, closed=False, requires_confirmation=True)
        if save_changes:
            # Commit the working copy then discard it.
            self.repository.commit_working_copy(game_id)
            self.repository.discard_working_copy(game_id)
            return CloseGameResult(
                game_id=game_id,
                closed=True,
                requires_confirmation=False,
                saved=True,
            )
        # Discard without saving.
        self.repository.discard_working_copy(game_id)
        return CloseGameResult(
            game_id=game_id,
            closed=True,
            requires_confirmation=False,
            discarded=True,
        )

    def render_pdf(
        self,
        *,
        game_id: str,
        diagram_size: int = 360,
        page_size: str = "a4",
    ) -> Path:
        """Render the game annotation to a PDF and return the output file path.

        Uses the working copy when a session is open, otherwise the canonical files.
        The PDF is written to ``<store_dir>/<game_id>/output.pdf``.

        Raises:
            MissingDependencyError: if no ``document_renderer`` was supplied.
            GameNotFoundError:      if ``game_id`` is not in the store.
            ValueError:             if any segment is missing a label or annotation text.
        """
        if self.document_renderer is None:
            raise MissingDependencyError("document_renderer is required")
        annotation = self._load_current_state(game_id)
        output_path = self.store_dir / game_id / "output.pdf"
        self.document_renderer.render(
            annotation,
            output_path=output_path,
            diagram_size=diagram_size,
            page_size=page_size,
            store_dir=self.store_dir,
        )
        return output_path

    def upload_to_lichess(self, *, game_id: str) -> str:
        """Upload the game PGN to Lichess and return the resulting analysis URL.

        Uses the working copy when a session is open, otherwise the canonical files.

        Raises:
            MissingDependencyError: if no ``lichess_uploader`` was supplied.
            GameNotFoundError:      if ``game_id`` is not in the store.
        """
        if self.lichess_uploader is None:
            raise MissingDependencyError("lichess_uploader is required")
        annotation = self._load_current_state(game_id)
        return self.lichess_uploader.upload(annotation.pgn)

    def list_segments(self, *, game_id: str) -> list[SegmentSummary]:
        """Return summaries for all segments in the open session, in order.

        Raises:
            SessionNotOpenError: if no working copy exists for ``game_id``.
        """
        annotation = self._load_session(game_id)
        return [_segment_summary(segment, annotation.pgn) for segment in derive_segments(annotation)]

    def view_segment(self, *, game_id: str, turning_point_ply: int) -> SegmentDetail:
        """Return full detail for the segment at ``turning_point_ply`` in the open session.

        Renders a diagram preview into the game's ``preview/`` directory when
        ``show_diagram`` is True and a diagram renderer is configured.

        Raises:
            SessionNotOpenError:  if no working copy exists for ``game_id``.
            SegmentNotFoundError: if ``turning_point_ply`` is not a turning point.
        """
        annotation = self._load_session(game_id)
        return self._segment_detail(annotation, turning_point_ply)

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _load_session(self, game_id: str) -> Annotation:
        """Load the working copy for an open session.

        Raises ``GameNotFoundError`` if the game does not exist, or
        ``SessionNotOpenError`` if no working copy is present.
        """
        if not self.repository.exists(game_id):
            raise GameNotFoundError(f"Game not found: {game_id}")
        if not self.repository.exists_working_copy(game_id):
            raise SessionNotOpenError(f"Session is not open for game: {game_id}")
        return self.repository.load_working_copy(game_id)

    def _load_current_state(self, game_id: str) -> Annotation:
        """Load the working copy if a session is open, otherwise load the canonical copy.

        Raises ``GameNotFoundError`` if the game does not exist.
        """
        if not self.repository.exists(game_id):
            raise GameNotFoundError(f"Game not found: {game_id}")
        if self.repository.exists_working_copy(game_id):
            return self.repository.load_working_copy(game_id)
        return self.repository.load(game_id)

    def _segment_content(self, annotation: Annotation, turning_point_ply: int):
        """Return the mutable ``SegmentContent`` for ``turning_point_ply``.

        Raises ``SegmentNotFoundError`` if the ply is not a turning point.
        """
        try:
            return annotation.segment_contents[turning_point_ply]
        except KeyError as exc:
            raise SegmentNotFoundError(
                f"Segment not found for turning point ply {turning_point_ply}"
            ) from exc

    def _segment_detail(
        self, annotation: Annotation, turning_point_ply: int
    ) -> SegmentDetail:
        """Build a ``SegmentDetail`` for ``turning_point_ply``, rendering a diagram preview if configured.

        Raises ``SegmentNotFoundError`` if the ply is not a turning point.
        """
        try:
            segment = find_segment_by_turning_point(annotation, turning_point_ply)
        except ValueError as exc:
            raise SegmentNotFoundError(str(exc)) from exc

        # Render a diagram preview into the game's preview directory if the
        # segment has show_diagram enabled and a renderer is available.
        diagram_path = None
        if segment.show_diagram and self.diagram_renderer is not None:
            cache_dir = self.store_dir / annotation.game_id / "preview"
            diagram_path = self.diagram_renderer.render(
                annotation.pgn,
                segment.end_ply,
                annotation.diagram_orientation,
                360,
                cache_dir,
            )

        return SegmentDetail(
            turning_point_ply=segment.turning_point_ply,
            start_ply=segment.start_ply,
            end_ply=segment.end_ply,
            move_range=san_move_range(annotation.pgn, segment.start_ply, segment.end_ply),
            label=segment.label,
            annotation=segment.annotation,
            move_list=format_move_list(
                annotation.pgn, segment.start_ply, segment.end_ply
            ),
            show_diagram=segment.show_diagram,
            diagram_path=diagram_path,
        )
