from __future__ import annotations

from pathlib import Path
from typing import Protocol

from chessplan.domain import GameAnnotations, GameRecord


class AnnotationStore(Protocol):
    def load_annotations(self, annotation_path: Path, pgn_path: Path, game: GameRecord) -> GameAnnotations: ...

    def save_annotations(self, annotation_path: Path, annotations: GameAnnotations) -> None: ...
