"""Command-line entry point for rendering annotated PGN files to PDF.

Installed as the ``chess-render`` console script by ``pyproject.toml``.
Validates the input path and output directory, delegates parsing and rendering
to the domain and adapter layers, and maps domain errors to non-zero exit codes
so callers can detect failures in shell scripts or CI pipelines.
"""

import argparse
import sys
from pathlib import Path

from render.adapters.chess_svg_diagram_renderer import ChessSvgDiagramRenderer
from render.adapters.pdf_renderer import ReportLabPdfRenderer
from render.domain.render_model import parse_pgn


def parse_args() -> argparse.Namespace:
    """Parse and return the command-line arguments for ``chess-render``.

    Arguments:
        pgn_file (positional): Path to the annotated ``.pgn`` input file.
        -o / --output (optional): Path for the output PDF.  Defaults to the
            input filename with ``.pgn`` replaced by ``.pdf`` in the current
            working directory.
        -r / --orientation (optional): ``"white"`` (default) or ``"black"`` —
            the side shown at the bottom of every board diagram.

    Returns:
        A populated :class:`argparse.Namespace` with attributes ``pgn_file``,
        ``output``, and ``orientation``.
    """

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
    """Entry point for the ``chess-render`` command.

    Validates that the input PGN file exists and that the output directory is
    accessible, then delegates to the rendering pipeline.  User-facing errors
    (missing file, bad PGN) are printed to ``stderr`` and cause a non-zero
    exit; unexpected exceptions propagate normally so stack traces are visible.

    Exit codes:
        0 — PDF written successfully.
        1 — Input file not found, output directory missing, or PGN parse error.
    """

    args = parse_args()
    pgn_path = Path(args.pgn_file)
    output_path = Path(args.output) if args.output else Path(pgn_path.stem + ".pdf")

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
