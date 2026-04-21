"""Command-line entry point for rendering annotated PGN files to PDF."""

import argparse
import sys
from pathlib import Path

from annotate.adapters.chess_svg_diagram_renderer import ChessSvgDiagramRenderer
from annotate.adapters.pdf_renderer import ReportLabPdfRenderer
from annotate.domain.render_model import parse_pgn


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the PDF rendering command."""

    parser = argparse.ArgumentParser(
        prog="chess-render",
        description="Render an annotated PGN file as a PDF.",
    )
    parser.add_argument("pgn_file", help="Path to the annotated .pgn input file")
    parser.add_argument("-o", "--output", default=None, help="Path for the PDF output file (default: input file with .pdf extension)")
    parser.add_argument(
        "-r", "--orientation",
        choices=["white", "black"],
        default="white",
        help="Board diagram orientation (default: white)",
    )
    return parser.parse_args()


def main() -> None:
    """Run the CLI, validating paths and translating user errors to exit codes."""

    args = parse_args()
    pgn_path = Path(args.pgn_file)
    output_path = Path(args.output) if args.output else pgn_path.with_suffix(".pdf")

    if not pgn_path.exists():
        print(f"chess-render: file not found: {pgn_path}", file=sys.stderr)
        sys.exit(1)
    if not output_path.parent.exists():
        print(f"chess-render: output directory does not exist: {output_path.parent}", file=sys.stderr)
        sys.exit(1)

    try:
        model = parse_pgn(pgn_path.read_text())
        renderer = ReportLabPdfRenderer(diagram_renderer=ChessSvgDiagramRenderer())
        renderer.render(model, output_path, args.orientation)
    except ValueError as exc:
        print(f"chess-render: {exc}", file=sys.stderr)
        sys.exit(1)
