from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chessplan.bootstrap import build_chess_book_service


def build_parser() -> argparse.ArgumentParser:
    """Create the standalone chess book CLI parser."""

    parser = argparse.ArgumentParser(description="Render an HTML chess book from PGN #chp comments")
    parser.add_argument("pgn", help="path to PGN file containing exactly one game")
    parser.add_argument(
        "--side",
        choices=("white", "black"),
        required=True,
        help="board orientation for inline SVG diagrams",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and render the chess book HTML."""

    parser = build_parser()
    args = parser.parse_args(argv)
    service = build_chess_book_service()
    try:
        print(service.render_html(Path(args.pgn), perspective=args.side), end="")
        return 0
    except FileNotFoundError as exc:
        print(f"File not found: {exc.filename}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
