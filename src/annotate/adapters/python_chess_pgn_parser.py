
import io

import chess.pgn

from annotate.ports import PGNParser


class PythonChessPGNParser(PGNParser):
    """Parse PGN text with ``python-chess`` and expose basic game metadata.

    This adapter converts raw PGN text into the small metadata structure
    needed by the current annotation workflow: player names, the PGN
    date header, and the number of plies in the main line. It performs
    no chess analysis beyond parsing the game structure and counting
    moves.
    """

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
