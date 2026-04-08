import io
import json
import shutil
from pathlib import Path

import chess.pgn

from annotate.domain.annotation import Annotation
from annotate.domain.segment import SegmentContent
from annotate.ports import GameRepository

TP_MARKER = "[%tp]"


def strip_comments_and_nags(pgn_text: str) -> str:
    """Return PGN text with comments and NAGs removed."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Could not parse PGN")

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
    game_data = json_data.get("game", {})
    segment_contents = {
        int(ply): SegmentContent(
            label=data.get("label", ""),
            annotation=data.get("annotation", data.get("commentary", "")),
            show_diagram=data.get("show_diagram", True),
        )
        for ply, data in json_data["segments"].items()
    }
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
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Could not parse PGN")
    return game


def turning_points_from_pgn(pgn_text: str) -> list[int]:
    """Extract turning-point plies from ``[%tp]`` markers in PGN comments."""
    game = _load_game(pgn_text)
    turning_points: list[int] = []
    for ply, node in enumerate(game.mainline(), start=0):
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
    """Serialize an annotation's turning points into PGN comments."""
    game = _load_game(annotation.pgn)
    for ply, node in enumerate(game.mainline(), start=0):
        if ply == 0:
            continue
        node.comment = TP_MARKER if ply in annotation.turning_points else ""
        node.starting_comment = ""
        node.nags.clear()
    exporter = chess.pgn.StringExporter(
        headers=True,
        variations=True,
        comments=True,
    )
    return game.accept(exporter)


def validate_pgn_json_sync(pgn_text: str, json_data: dict) -> None:
    """Ensure the PGN markers and JSON segment keys match exactly."""
    pgn_turning_points = turning_points_from_pgn(pgn_text)
    json_turning_points = sorted(int(ply) for ply in json_data["segments"])
    if pgn_turning_points != json_turning_points:
        raise ValueError(
            "Turning points in annotated PGN do not match annotation.json segment keys"
        )


class PGNFileGameRepository(GameRepository):
    """Persist each game in its own directory under the store root."""

    MAIN_PGN = "annotated.pgn"
    MAIN_JSON = "annotation.json"
    WORK_PGN = "annotated.pgn.work"
    WORK_JSON = "annotation.json.work"
    OUTPUT_PDF = "output.pdf"

    def __init__(self, store_dir: Path) -> None:
        self._store = Path(store_dir)
        self._store.mkdir(parents=True, exist_ok=True)

    def game_dir(self, game_id: str | int) -> Path:
        return self._store / str(game_id)

    def main_pgn_path(self, game_id: str | int) -> Path:
        return self.game_dir(game_id) / self.MAIN_PGN

    def main_json_path(self, game_id: str | int) -> Path:
        return self.game_dir(game_id) / self.MAIN_JSON

    def work_pgn_path(self, game_id: str | int) -> Path:
        return self.game_dir(game_id) / self.WORK_PGN

    def work_json_path(self, game_id: str | int) -> Path:
        return self.game_dir(game_id) / self.WORK_JSON

    def output_pdf_path(self, game_id: str | int) -> Path:
        return self.game_dir(game_id) / self.OUTPUT_PDF

    def save(self, annotation: Annotation) -> None:
        game_dir = self.game_dir(annotation.game_id)
        game_dir.mkdir(parents=True, exist_ok=True)
        pgn_text = pgn_with_turning_points(annotation)
        json_data = _annotation_json_data(annotation)
        validate_pgn_json_sync(pgn_text, json_data)
        self.main_pgn_path(annotation.game_id).write_text(pgn_text)
        self.main_json_path(annotation.game_id).write_text(
            json.dumps(json_data, indent=2, sort_keys=True)
        )

    def load(self, game_id: str | int) -> Annotation:
        pgn_path = self.main_pgn_path(game_id)
        json_path = self.main_json_path(game_id)
        if not pgn_path.exists() or not json_path.exists():
            raise FileNotFoundError(f"No game found: {game_id}")
        pgn_text = pgn_path.read_text()
        json_data = json.loads(json_path.read_text())
        validate_pgn_json_sync(pgn_text, json_data)
        return _annotation_from_json_and_pgn(
            game_id=str(game_id),
            pgn_text=pgn_text,
            json_data=json_data,
        )

    def list_all(self) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        for path in sorted(self._store.iterdir()):
            if not path.is_dir():
                continue
            pgn_path = path / self.MAIN_PGN
            json_path = path / self.MAIN_JSON
            if not pgn_path.exists() or not json_path.exists():
                continue
            json_data = json.loads(json_path.read_text())
            title = json_data.get("game", {}).get("title", "")
            result.append((path.name, title))
        return result

    def exists_working_copy(self, game_id: str | int) -> bool:
        work_pgn = self.work_pgn_path(game_id)
        work_json = self.work_json_path(game_id)
        return work_pgn.exists() or work_json.exists()

    def save_working_copy(self, annotation: Annotation) -> None:
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
        pgn_path = self.work_pgn_path(game_id)
        json_path = self.work_json_path(game_id)
        if not pgn_path.exists() or not json_path.exists():
            raise FileNotFoundError(f"No working copy found: {game_id}")
        pgn_text = pgn_path.read_text()
        json_data = json.loads(json_path.read_text())
        validate_pgn_json_sync(pgn_text, json_data)
        return _annotation_from_json_and_pgn(
            game_id=str(game_id),
            pgn_text=pgn_text,
            json_data=json_data,
        )

    def discard_working_copy(self, game_id: str | int) -> None:
        for path in (self.work_pgn_path(game_id), self.work_json_path(game_id)):
            if path.exists():
                path.unlink()

    def commit_working_copy(self, game_id: str | int) -> None:
        work_pgn = self.work_pgn_path(game_id)
        work_json = self.work_json_path(game_id)
        if not work_pgn.exists() or not work_json.exists():
            raise FileNotFoundError(f"No working copy to commit: {game_id}")
        shutil.copy2(work_pgn, self.main_pgn_path(game_id))
        shutil.copy2(work_json, self.main_json_path(game_id))

    def has_unsaved_working_copy(self, game_id: str | int) -> bool:
        work_pgn = self.work_pgn_path(game_id)
        work_json = self.work_json_path(game_id)
        main_pgn = self.main_pgn_path(game_id)
        main_json = self.main_json_path(game_id)
        if not work_pgn.exists() or not work_json.exists():
            return False
        if not main_pgn.exists() or not main_json.exists():
            return True
        return (
            work_pgn.read_text() != main_pgn.read_text()
            or work_json.read_text() != main_json.read_text()
        )

    def stale_working_copies(self) -> list[str]:
        result: list[str] = []
        for path in sorted(self._store.iterdir()):
            if not path.is_dir():
                continue
            if (path / self.WORK_PGN).exists() or (path / self.WORK_JSON).exists():
                result.append(path.name)
        return result

    def next_id(self) -> int:
        """Return the next integer-like game id for backward compatibility."""
        max_id = 0
        for path in self._store.iterdir():
            if not path.is_dir():
                continue
            try:
                max_id = max(max_id, int(path.name))
            except ValueError:
                pass
        return max_id + 1


# Backward-compatible adapter name retained while CLI modules migrate.
JSONFileAnnotationRepository = PGNFileGameRepository
