# annotate.server.app
import argparse

import uvicorn
from fastapi import FastAPI

from annotate.adapters.json_file_annotation_repository import JSONFileAnnotationRepository
from annotate.adapters.lichess_api_uploader import LichessAPIUploader
from annotate.adapters.markdown_html_pdf_renderer import MarkdownHTMLPDFRenderer
from annotate.adapters.python_chess_pgn_parser import PythonChessPGNParser
from annotate.config import get_config
from annotate.server import deps
from annotate.server.routes import games, outputs, segments, sessions
from annotate.use_cases import AnnotationService


def _create_service() -> AnnotationService:
    """Wire all concrete adapters and return the ``AnnotationService`` singleton."""
    config = get_config()
    return AnnotationService(
        repository=JSONFileAnnotationRepository(config.store_dir),
        pgn_parser=PythonChessPGNParser(),
        store_dir=config.store_dir,
        document_renderer=MarkdownHTMLPDFRenderer(),
        lichess_uploader=LichessAPIUploader(),
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    deps.init_service(_create_service())

    app = FastAPI(title="Chess Annotator API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(games.router)
    app.include_router(sessions.router)
    app.include_router(segments.router)
    app.include_router(outputs.router)

    return app


def main() -> None:
    """Entry point for the ``chess-server`` command."""
    parser = argparse.ArgumentParser(description="Chess Annotator API server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    uvicorn.run(create_app(), host=args.host, port=args.port)
