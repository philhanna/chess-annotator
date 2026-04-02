# chess_annotate.adapters.repository

import json
import shutil
from pathlib import Path

from chess_annotate.domain.model import Annotation, Segment
from chess_annotate.ports import AnnotationRepository


def _to_dict(annotation: Annotation) -> dict:
    return {
        "annotation_id": annotation.annotation_id,
        "title": annotation.title,
        "author": annotation.author,
        "date": annotation.date,
        "pgn": annotation.pgn,
        "player_side": annotation.player_side,
        "diagram_orientation": annotation.diagram_orientation,
        "segments": [
            {
                "start_ply": seg.start_ply,
                "label": seg.label,
                "commentary": seg.commentary,
                "show_diagram": seg.show_diagram,
            }
            for seg in annotation.segments
        ],
    }


def _from_dict(data: dict) -> Annotation:
    segments = [
        Segment(
            start_ply=s["start_ply"],
            label=s.get("label"),
            commentary=s.get("commentary", ""),
            show_diagram=s.get("show_diagram", False),
        )
        for s in data["segments"]
    ]
    return Annotation(
        annotation_id=data["annotation_id"],
        title=data["title"],
        author=data["author"],
        date=data["date"],
        pgn=data["pgn"],
        player_side=data["player_side"],
        diagram_orientation=data["diagram_orientation"],
        segments=segments,
    )


class JSONFileAnnotationRepository(AnnotationRepository):

    def __init__(self, store_dir: Path) -> None:
        self._store = store_dir
        self._annotations_dir = store_dir / "annotations"
        self._work_dir = store_dir / "work"
        self._cache_dir = store_dir / "cache"
        self._annotations_dir.mkdir(parents=True, exist_ok=True)
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Main store
    # ------------------------------------------------------------------

    def _main_path(self, annotation_id: str) -> Path:
        return self._annotations_dir / f"{annotation_id}.json"

    def save(self, annotation: Annotation) -> None:
        path = self._main_path(annotation.annotation_id)
        path.write_text(json.dumps(_to_dict(annotation), indent=2))

    def load(self, annotation_id: str) -> Annotation:
        path = self._main_path(annotation_id)
        if not path.exists():
            raise FileNotFoundError(f"No annotation found: {annotation_id}")
        return _from_dict(json.loads(path.read_text()))

    def list_all(self) -> list[tuple[str, str]]:
        result = []
        for p in sorted(self._annotations_dir.glob("*.json")):
            data = json.loads(p.read_text())
            result.append((data["annotation_id"], data["title"]))
        return result

    # ------------------------------------------------------------------
    # Working copy
    # ------------------------------------------------------------------

    def _work_path(self, annotation_id: str) -> Path:
        return self._work_dir / f"{annotation_id}.json"

    def exists_working_copy(self, annotation_id: str) -> bool:
        return self._work_path(annotation_id).exists()

    def save_working_copy(self, annotation: Annotation) -> None:
        path = self._work_path(annotation.annotation_id)
        path.write_text(json.dumps(_to_dict(annotation), indent=2))

    def load_working_copy(self, annotation_id: str) -> Annotation:
        path = self._work_path(annotation_id)
        if not path.exists():
            raise FileNotFoundError(f"No working copy found: {annotation_id}")
        return _from_dict(json.loads(path.read_text()))

    def discard_working_copy(self, annotation_id: str) -> None:
        path = self._work_path(annotation_id)
        if path.exists():
            path.unlink()

    def commit_working_copy(self, annotation_id: str) -> None:
        work_path = self._work_path(annotation_id)
        if not work_path.exists():
            raise FileNotFoundError(f"No working copy to commit: {annotation_id}")
        shutil.copy2(work_path, self._main_path(annotation_id))
        work_path.unlink()

    def stale_working_copies(self) -> list[str]:
        return [p.stem for p in self._work_dir.glob("*.json")]
