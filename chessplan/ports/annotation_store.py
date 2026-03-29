from __future__ import annotations

from pathlib import Path
from typing import Protocol

from chessplan.domain import GameAnnotations, GameRecord


class AnnotationStore(Protocol):
    """Port for reading and writing persisted review annotations."""

    def load_annotations(self, annotation_path: Path, pgn_path: Path, game: GameRecord) -> GameAnnotations:
        """Load annotations for a game or provide an initialized default."""
        ...

    def save_annotations(self, annotation_path: Path, annotations: GameAnnotations) -> None:
        """Persist the supplied annotations to `annotation_path`."""
        ...
