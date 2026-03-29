from __future__ import annotations

from chessplan.adapters.json_annotations import JsonAnnotationStore
from chessplan.adapters.pgn_reader import PythonChessGameLoader
from chessplan.use_cases.review_service import ReviewService


def build_review_service() -> ReviewService:
    """Assemble the default review service with filesystem-backed adapters."""

    return ReviewService(
        game_loader=PythonChessGameLoader(),
        annotation_store=JsonAnnotationStore(),
    )
