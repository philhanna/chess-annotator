# annotate.render_cli
import argparse
import sys
from pathlib import Path

from annotate.adapters.pgn_pdf_renderer import render_pdf


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="chess-render",
        description="Render an annotated PGN file as a PDF.",
    )
    parser.add_argument("pgn_file", help="Path to the annotated .pgn input file")
    parser.add_argument("-o", "--output", required=True, help="Path for the PDF output file")
    parser.add_argument(
        "-r", "--orientation",
        choices=["white", "black"],
        default="white",
        help="Board diagram orientation (default: white)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    pgn_path = Path(args.pgn_file)
    output_path = Path(args.output)

    if not pgn_path.exists():
        print(f"chess-render: file not found: {pgn_path}", file=sys.stderr)
        sys.exit(1)
    if not output_path.parent.exists():
        print(f"chess-render: output directory does not exist: {output_path.parent}", file=sys.stderr)
        sys.exit(1)

    try:
        render_pdf(pgn_path.read_text(), output_path=output_path, orientation=args.orientation)
    except ValueError as exc:
        print(f"chess-render: {exc}", file=sys.stderr)
        sys.exit(1)
