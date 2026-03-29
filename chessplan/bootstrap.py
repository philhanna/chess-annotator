from __future__ import annotations

from chessplan.adapters.json_annotations import JsonAnnotationStore
from chessplan.adapters.pgn_reader import PythonChessGameLoader
from chessplan.use_cases.chess_book import ChessBookService
from chessplan.use_cases.review_service import ReviewService


def build_review_service() -> ReviewService:
    """Assemble the default review service with filesystem-backed adapters."""

    return ReviewService(
        game_loader=PythonChessGameLoader(),
        annotation_store=JsonAnnotationStore(),
    )


def build_chess_book_service() -> ChessBookService:
    """Assemble the HTML chess book workflow."""

    return ChessBookService(game_loader=PythonChessGameLoader())
