#!/usr/bin/env python3
"""Simple CLI for plan-oriented chess game review.

Overview:
- Always expects exactly one game in the PGN file
- Shows numbered moves in order
- Add labeled move-range annotations such as "Plan 1" or "Gap"
- Save annotations to JSON
- Print a review summary grouped by blocks

Dependency:
    pip install python-chess

Examples:
    python chessplan.py show game.pgn
    python chessplan.py annotate game.pgn
    python chessplan.py summary game.pgn

Annotation file default:
    <pgn-path>.plans.json
"""

from __future__ import annotations

from chessplan.adapters.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
