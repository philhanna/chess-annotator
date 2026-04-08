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
from annotate.use_cases.interactors import merge_segment, split_segment


class UseCaseError(Exception):
    """Base class for application-layer errors."""


class GameNotFoundError(UseCaseError):
    """Raised when the requested game does not exist."""


class SessionNotOpenError(UseCaseError):
    """Raised when a use case requires working files but none exist."""


class SegmentNotFoundError(UseCaseError):
    """Raised when the requested segment does not exist."""


class OverwriteRequiredError(UseCaseError):
    """Raised when a target game already exists and overwrite was not allowed."""


class MissingDependencyError(UseCaseError):
    """Raised when a use case needs an adapter that was not supplied."""


@dataclass(frozen=True)
class SegmentSummary:
    turning_point_ply: int
    start_ply: int
    end_ply: int
    move_range: str
    label: str
    has_annotation: bool
    show_diagram: bool


@dataclass(frozen=True)
class SegmentDetail:
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
    game_id: str
    title: str
    session_open: bool
    has_unsaved_changes: bool
    segments: list[SegmentSummary]
    resumed: bool = False


@dataclass(frozen=True)
class CloseGameResult:
    game_id: str
    closed: bool
    requires_confirmation: bool
    saved: bool = False
    discarded: bool = False


def _segment_summary(segment: SegmentView, pgn: str) -> SegmentSummary:
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
    return GameState(
        game_id=annotation.game_id,
        title=annotation.title,
        session_open=session_open,
        has_unsaved_changes=repo.has_unsaved_working_copy(annotation.game_id),
        segments=[_segment_summary(segment, annotation.pgn) for segment in derive_segments(annotation)],
        resumed=resumed,
    )


def _select_game_text(pgn_text: str, game_index: int) -> str:
    games = []
    stream = io.StringIO(pgn_text)
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


class AnnotationService:
    """Application services implementing the documented use cases."""

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
        if self.repository.exists(game_id) and not overwrite:
            raise OverwriteRequiredError(f"Game id already exists: {game_id}")
        if self.repository.exists(game_id):
            self.repository.delete(game_id)

        selected_game = _select_game_text(pgn_text, game_index)
        cleaned_pgn = strip_comments_and_nags(selected_game)
        info = self.pgn_parser.parse(cleaned_pgn)
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
        self.repository.save(annotation)
        self.repository.save_working_copy(annotation)
        return _game_state(self.repository, annotation, session_open=True)

    def list_games(self) -> list[GameSummary]:
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
        if not self.repository.exists(game_id):
            raise GameNotFoundError(f"Game not found: {game_id}")
        if self.repository.exists_working_copy(game_id):
            annotation = self.repository.load_working_copy(game_id)
            return _game_state(
                self.repository,
                annotation,
                session_open=True,
                resumed=True,
            )
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
        if not self.repository.exists(source_game_id):
            raise GameNotFoundError(f"Game not found: {source_game_id}")
        if self.repository.exists(new_game_id):
            if not overwrite:
                raise OverwriteRequiredError(f"Game id already exists: {new_game_id}")
            self.repository.delete(new_game_id)

        if self.repository.exists_working_copy(source_game_id):
            annotation = self.repository.load_working_copy(source_game_id)
        else:
            annotation = self.repository.load(source_game_id)
        annotation.game_id = new_game_id
        annotation.annotation_id = new_game_id
        self.repository.save(annotation)

    def delete_game(self, game_id: str) -> None:
        if not self.repository.exists(game_id):
            raise GameNotFoundError(f"Game not found: {game_id}")
        self.repository.delete(game_id)

    def add_turning_point(
        self, *, game_id: str, ply: int, label: str = ""
    ) -> list[SegmentSummary]:
        annotation = self._load_session(game_id)
        updated = split_segment(annotation, ply, label)
        self.repository.save_working_copy(updated)
        return [_segment_summary(segment, updated.pgn) for segment in derive_segments(updated)]

    def remove_turning_point(
        self, *, game_id: str, ply: int, force: bool = False
    ) -> list[SegmentSummary]:
        annotation = self._load_session(game_id)
        updated, merged = merge_segment(annotation, ply, force=force)
        if not merged:
            raise UseCaseError("Turning point has content; force is required to remove it")
        self.repository.save_working_copy(updated)
        return [_segment_summary(segment, updated.pgn) for segment in derive_segments(updated)]

    def set_segment_label(
        self, *, game_id: str, turning_point_ply: int, label: str
    ) -> SegmentDetail:
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
        annotation = self._load_session(game_id)
        content = self._segment_content(annotation, turning_point_ply)
        content.show_diagram = not content.show_diagram
        self.repository.save_working_copy(annotation)
        return self._segment_detail(annotation, turning_point_ply)

    def save_session(self, game_id: str) -> GameState:
        annotation = self._load_session(game_id)
        self.repository.save_working_copy(annotation)
        self.repository.commit_working_copy(game_id)
        return _game_state(self.repository, self.repository.load_working_copy(game_id), session_open=True)

    def close_game(
        self, game_id: str, save_changes: bool | None = None
    ) -> CloseGameResult:
        self._load_session(game_id)
        has_unsaved = self.repository.has_unsaved_working_copy(game_id)
        if not has_unsaved:
            self.repository.discard_working_copy(game_id)
            return CloseGameResult(game_id=game_id, closed=True, requires_confirmation=False)
        if save_changes is None:
            return CloseGameResult(game_id=game_id, closed=False, requires_confirmation=True)
        if save_changes:
            self.repository.commit_working_copy(game_id)
            self.repository.discard_working_copy(game_id)
            return CloseGameResult(
                game_id=game_id,
                closed=True,
                requires_confirmation=False,
                saved=True,
            )
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
        if self.lichess_uploader is None:
            raise MissingDependencyError("lichess_uploader is required")
        annotation = self._load_current_state(game_id)
        return self.lichess_uploader.upload(annotation.pgn)

    def list_segments(self, *, game_id: str) -> list[SegmentSummary]:
        annotation = self._load_session(game_id)
        return [_segment_summary(segment, annotation.pgn) for segment in derive_segments(annotation)]

    def view_segment(self, *, game_id: str, turning_point_ply: int) -> SegmentDetail:
        annotation = self._load_session(game_id)
        return self._segment_detail(annotation, turning_point_ply)

    def _load_session(self, game_id: str) -> Annotation:
        if not self.repository.exists(game_id):
            raise GameNotFoundError(f"Game not found: {game_id}")
        if not self.repository.exists_working_copy(game_id):
            raise SessionNotOpenError(f"Session is not open for game: {game_id}")
        return self.repository.load_working_copy(game_id)

    def _load_current_state(self, game_id: str) -> Annotation:
        if not self.repository.exists(game_id):
            raise GameNotFoundError(f"Game not found: {game_id}")
        if self.repository.exists_working_copy(game_id):
            return self.repository.load_working_copy(game_id)
        return self.repository.load(game_id)

    def _segment_content(self, annotation: Annotation, turning_point_ply: int):
        try:
            return annotation.segment_contents[turning_point_ply]
        except KeyError as exc:
            raise SegmentNotFoundError(
                f"Segment not found for turning point ply {turning_point_ply}"
            ) from exc

    def _segment_detail(
        self, annotation: Annotation, turning_point_ply: int
    ) -> SegmentDetail:
        try:
            segment = find_segment_by_turning_point(annotation, turning_point_ply)
        except ValueError as exc:
            raise SegmentNotFoundError(str(exc)) from exc

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
