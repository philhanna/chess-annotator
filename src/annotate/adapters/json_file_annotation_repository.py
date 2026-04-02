import json
import shutil
from pathlib import Path

from annotate.domain.annotation import Annotation
from annotate.domain.segment import Segment
from annotate.ports import AnnotationRepository


def to_dict(annotation: Annotation) -> dict:
    """Convert an :class:`Annotation` domain object into JSON-ready data.

    The returned dictionary mirrors the on-disk schema used by the file
    repository. Nested :class:`Segment` instances are flattened into
    plain dictionaries so the structure can be serialized directly with
    :mod:`json`.
    """

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


def from_dict(data: dict) -> Annotation:
    """Build an :class:`Annotation` from a decoded JSON dictionary.

    This is the inverse of :func:`to_dict` for repository persistence.
    Missing optional segment fields are normalized to the defaults used
    by the domain model so older or partial JSON documents can still be
    loaded safely.
    """

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
        annotation_id=int(data["annotation_id"]),
        title=data["title"],
        author=data["author"],
        date=data["date"],
        pgn=data["pgn"],
        player_side=data["player_side"],
        diagram_orientation=data["diagram_orientation"],
        segments=segments,
    )


class JSONFileAnnotationRepository(AnnotationRepository):
    """Persist annotations as one JSON file per annotation on disk.

    This adapter is the concrete file-system implementation of the
    ``AnnotationRepository`` port. It manages three sibling directories
    rooted under ``store_dir``:

    - ``annotations/`` stores the canonical saved version of each
      annotation as ``<annotation_id>.json``.
    - ``work/`` stores temporary working copies used during an editing
      session so unsaved changes do not overwrite the canonical file.
    - ``cache/`` is created here for related render artifacts, even
      though this repository class does not currently read or write the
      cached files directly.

    The repository exposes two related workflows:

    - Main-store operations such as :meth:`save`, :meth:`load`, and
      :meth:`list_all`, which operate on the canonical annotation files.
    - Working-copy operations such as :meth:`save_working_copy`,
      :meth:`load_working_copy`, :meth:`discard_working_copy`, and
      :meth:`commit_working_copy`, which support the author's edit
      session lifecycle.

    Data is serialized with the module-level ``to_dict`` and
    ``from_dict`` helpers, which map between domain objects and the
    JSON structure stored on disk.

    Instances eagerly create the required directory structure during
    initialization, so callers can assume the repository is immediately
    ready for use once constructed.
    """

    def __init__(self, store_dir: Path) -> None:
        """Initialize the repository and create its backing directories."""
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

    def main_path(self, annotation_id: int) -> Path:
        """Return the canonical JSON file path for ``annotation_id``."""
        return self._annotations_dir / f"{annotation_id!s}.json"

    def save(self, annotation: Annotation) -> None:
        """Write ``annotation`` to its canonical JSON file in ``annotations/``."""
        path = self.main_path(annotation.annotation_id)
        path.write_text(json.dumps(to_dict(annotation), indent=2))

    def load(self, annotation_id: int) -> Annotation:
        """Load an annotation from its canonical JSON file.

        Raises ``FileNotFoundError`` when no saved annotation exists for
        the requested identifier.
        """
        path = self.main_path(annotation_id)
        if not path.exists():
            raise FileNotFoundError(f"No annotation found: {annotation_id}")
        return from_dict(json.loads(path.read_text()))

    def list_all(self) -> list[tuple[int, str]]:
        """Return all saved annotations as ``(annotation_id, title)`` pairs.

        Results are ordered by filename so listings are stable across
        repeated invocations.
        """
        result = []
        for p in sorted(self._annotations_dir.glob("*.json")):
            data = json.loads(p.read_text())
            result.append((int(data["annotation_id"]), data["title"]))
        return result

    # ------------------------------------------------------------------
    # Working copy
    # ------------------------------------------------------------------

    def work_path(self, annotation_id: int) -> Path:
        """Return the working-copy JSON path for ``annotation_id``."""
        return self._work_dir / f"{annotation_id!s}.json"

    def exists_working_copy(self, annotation_id: int) -> bool:
        """Report whether a working-copy file exists for ``annotation_id``."""
        return self.work_path(annotation_id).exists()

    def save_working_copy(self, annotation: Annotation) -> None:
        """Write ``annotation`` to the ``work/`` directory as a working copy."""
        path = self.work_path(annotation.annotation_id)
        path.write_text(json.dumps(to_dict(annotation), indent=2))

    def load_working_copy(self, annotation_id: int) -> Annotation:
        """Load an annotation from its working-copy JSON file.

        Raises ``FileNotFoundError`` when no working copy exists for the
        requested identifier.
        """
        path = self.work_path(annotation_id)
        if not path.exists():
            raise FileNotFoundError(f"No working copy found: {annotation_id}")
        return from_dict(json.loads(path.read_text()))

    def discard_working_copy(self, annotation_id: int) -> None:
        """Remove the working-copy file for ``annotation_id`` if present."""
        path = self.work_path(annotation_id)
        if path.exists():
            path.unlink()

    def commit_working_copy(self, annotation_id: int) -> None:
        """Promote a working copy into the canonical store and delete it.

        The working-copy file is copied over the main annotation file so
        metadata such as file timestamps are preserved where possible.
        Raises ``FileNotFoundError`` if no working copy exists.
        """
        work_path = self.work_path(annotation_id)
        if not work_path.exists():
            raise FileNotFoundError(f"No working copy to commit: {annotation_id}")
        shutil.copy2(work_path, self.main_path(annotation_id))
        work_path.unlink()

    def stale_working_copies(self) -> list[int]:
        """Return annotation ids that currently have working-copy files."""
        result = []
        for p in self._work_dir.glob("*.json"):
            try:
                result.append(int(p.stem))
            except ValueError:
                pass
        return result

    def next_id(self) -> int:
        """Return the next annotation id: one greater than the highest id in the store."""
        max_id = 0
        for p in self._annotations_dir.glob("*.json"):
            try:
                max_id = max(max_id, int(p.stem))
            except ValueError:
                pass
        return max_id + 1
