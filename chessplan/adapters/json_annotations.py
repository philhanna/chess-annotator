from __future__ import annotations

import json
from pathlib import Path

from chessplan.domain import GameAnnotations, GameRecord


class JsonAnnotationStore:
    def load_annotations(self, annotation_path: Path, pgn_path: Path, game: GameRecord) -> GameAnnotations:
        if not annotation_path.exists():
            return GameAnnotations(
                pgn_path=str(pgn_path),
                event=game.headers.event,
                white=game.headers.white,
                black=game.headers.black,
                result=game.headers.result,
            )

        with annotation_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise SystemExit(f"Invalid annotation file format: {annotation_path}")
        return GameAnnotations.from_json_dict(data)

    def save_annotations(self, annotation_path: Path, annotations: GameAnnotations) -> None:
        with annotation_path.open("w", encoding="utf-8") as fh:
            json.dump(annotations.to_json_dict(), fh, indent=2)
            fh.write("")
