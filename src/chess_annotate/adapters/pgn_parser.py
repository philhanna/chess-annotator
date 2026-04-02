# chess_annotate.adapters.pgn_parser
from __future__ import annotations

import io

import chess.pgn

from chess_annotate.domain.ports import PGNParser


class PythonChessPGNParser(PGNParser):

    def parse(self, pgn_text: str) -> dict:
        """Parse PGN text and return metadata dict.

        Returns:
            {
                "white": str,
                "black": str,
                "date": str,       # from PGN header, may be "???" if absent
                "total_plies": int,
            }

        Raises:
            ValueError: if the PGN cannot be parsed.
        """
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game is None:
            raise ValueError("Could not parse PGN: no game found")

        headers = game.headers
        white = headers.get("White", "?")
        black = headers.get("Black", "?")
        date = headers.get("Date", "???")

        total_plies = sum(1 for _ in game.mainline_moves())

        return {
            "white": white,
            "black": black,
            "date": date,
            "total_plies": total_plies,
        }
