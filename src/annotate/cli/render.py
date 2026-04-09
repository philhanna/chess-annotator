import argparse
import sys

from annotate.adapters.json_file_annotation_repository import JSONFileAnnotationRepository
from annotate.adapters.markdown_html_pdf_renderer import MarkdownHTMLPDFRenderer
from annotate.adapters.python_chess_pgn_parser import PythonChessPGNParser
from annotate.config import get_config
from annotate.use_cases import AnnotationService, GameNotFoundError, UseCaseError


def build_service() -> AnnotationService:
    config = get_config()
    return AnnotationService(
        repository=JSONFileAnnotationRepository(config.store_dir),
        pgn_parser=PythonChessPGNParser(),
        store_dir=config.store_dir,
        document_renderer=MarkdownHTMLPDFRenderer(),
    )


def main() -> None:
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
    args = parser.parse_args()

    service = build_service()
    try:
        output_path = service.render_pdf(
            game_id=args.game_id,
            diagram_size=args.size,
            page_size=args.page,
        )
    except GameNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except (UseCaseError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Rendered: {output_path}")
