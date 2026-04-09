import argparse
import sys
from pathlib import Path

from annotate.adapters.json_file_annotation_repository import JSONFileAnnotationRepository
from annotate.adapters.pgn_file_game_repository import strip_comments_and_nags
from annotate.adapters.markdown_html_pdf_renderer import MarkdownHTMLPDFRenderer
from annotate.adapters.python_chess_pgn_parser import PythonChessPGNParser
from annotate.config import get_config
from annotate.use_cases import AnnotationService, GameNotFoundError, UseCaseError


def build_repository() -> JSONFileAnnotationRepository:
    """Construct and return the repository used by the render CLI."""
    config = get_config()
    return JSONFileAnnotationRepository(config.store_dir)


def build_service(
    repository: JSONFileAnnotationRepository | None = None,
) -> AnnotationService:
    """Construct and return an ``AnnotationService`` wired for PDF rendering.

    Only the repository, PGN parser, and document renderer adapters are wired;
    the Lichess uploader and diagram renderer are not needed for this command.
    """
    config = get_config()
    repository = repository or build_repository()
    return AnnotationService(
        repository=repository,
        pgn_parser=PythonChessPGNParser(),
        store_dir=config.store_dir,
        document_renderer=MarkdownHTMLPDFRenderer(),
    )


def _load_current_annotation(
    repository: JSONFileAnnotationRepository,
    game_id: str,
):
    """Load the working copy when present, otherwise load the canonical game."""
    if not repository.exists(game_id):
        raise GameNotFoundError(f"Game not found: {game_id}")
    if repository.exists_working_copy(game_id):
        return repository.load_working_copy(game_id)
    return repository.load(game_id)


def main() -> None:
    """Entry point for the ``chess-render`` command-line tool.

    Parses arguments, renders the requested game to a PDF, and prints the
    output path on success. Exits with status 1 on any error.
    """
    config = get_config()

    parser = argparse.ArgumentParser(
        description="Render a chess annotation to a book-quality PDF."
    )
    parser.add_argument(
        "game_id",
        help="Game id to render",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=config.diagram_size,
        metavar="PX",
        help=f"Diagram size in pixels (default: {config.diagram_size})",
    )
    parser.add_argument(
        "--page",
        default=config.page_size,
        choices=["a4", "letter"],
        metavar="SIZE",
        help=f"Page size: a4 or letter (default: {config.page_size})",
    )
    parser.add_argument(
        "-d",
        "--dir",
        type=Path,
        default=Path.cwd(),
        metavar="DIR",
        help="Directory for output artifacts (default: current directory)",
    )
    args = parser.parse_args()

    repo = build_repository()
    service = build_service(repository=repo)
    try:
        output_dir = args.dir
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = output_dir / f"{args.game_id}.pdf"
        output_path = service.render_pdf(
            game_id=args.game_id,
            diagram_size=args.size,
            page_size=args.page,
            output_path=pdf_path,
        )
        annotation = _load_current_annotation(repo, args.game_id)
        pgn_path = output_dir / f"{args.game_id}.pgn"
        pgn_path.write_text(strip_comments_and_nags(annotation.pgn))
    except GameNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except (UseCaseError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Rendered PDF: {output_path}")
    print(f"Exported PGN: {pgn_path}")
