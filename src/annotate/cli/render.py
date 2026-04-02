"""chess-render — render an annotation to a book-quality PDF."""

import argparse
import sys
from pathlib import Path

from annotate.adapters.json_file_annotation_repository import JSONFileAnnotationRepository
from annotate.adapters.markdown_html_pdf_renderer import MarkdownHTMLPDFRenderer
from annotate.config import get_config


def main() -> None:
    """Run the ``chess-render`` command-line tool."""
    config = get_config()

    parser = argparse.ArgumentParser(
        description="Render a chess annotation to a book-quality PDF."
    )
    parser.add_argument(
        "filename",
        help="Annotation ID or filename (e.g. abc123.json) to render",
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
        "--out",
        default=None,
        metavar="PATH",
        help="Output PDF path (default: <annotation_id>.pdf in current directory)",
    )
    args = parser.parse_args()

    store_dir = config.store_dir
    repo = JSONFileAnnotationRepository(store_dir)

    raw = args.filename
    if raw.endswith(".json"):
        raw = raw[:-5]
    try:
        annotation_id = int(raw)
    except ValueError:
        print(f"Error: invalid annotation id: {raw!r}", file=sys.stderr)
        sys.exit(1)

    try:
        annotation = repo.load(annotation_id)
    except FileNotFoundError:
        print(f"Error: annotation not found: {annotation_id}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.out) if args.out else Path(f"{annotation_id}.pdf")

    renderer = MarkdownHTMLPDFRenderer()
    try:
        renderer.render(
            annotation,
            output_path=output_path,
            diagram_size=args.size,
            page_size=args.page,
            store_dir=store_dir,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Rendered: {output_path}")
