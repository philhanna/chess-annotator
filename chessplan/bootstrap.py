from __future__ import annotations

from chessplan.adapters.json_annotations import JsonAnnotationStore
from chessplan.adapters.pgn_reader import PythonChessGameLoader
from chessplan.usecases.review_service import ReviewService


def build_review_service() -> ReviewService:
    return ReviewService(
        game_loader=PythonChessGameLoader(),
        annotation_store=JsonAnnotationStore(),
    )
