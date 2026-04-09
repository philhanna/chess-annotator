import io

import chess.pgn

from annotate.ports import PGNParser


class PythonChessPGNParser(PGNParser):
    """Parse PGN text with ``python-chess`` and return basic game metadata.

    Extracts the player names, Date header, and total ply count from the first
    game in the PGN string. No chess analysis is performed; the parser only reads
    the headers and counts the moves in the main line.
    """

    def parse(self, pgn_text: str) -> dict:
        """Parse ``pgn_text`` and return a metadata dict.

        Returns:
            A dict with the following keys:

            * ``"white"``       — name of the White player; ``"?"`` if absent.
            * ``"black"``       — name of the Black player; ``"?"`` if absent.
            * ``"date"``        — PGN Date header value; ``"???"`` if absent.
            * ``"total_plies"`` — number of half-moves in the main line.

        Raises:
            ValueError: if the PGN cannot be parsed or contains no game.
        """
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game is None:
            raise ValueError("Could not parse PGN: no game found")

        headers = game.headers
        # Use sensible fallbacks for missing header values.
        white = headers.get("White", "?")
        black = headers.get("Black", "?")
        date = headers.get("Date", "???")

        # Count plies by iterating the main-line move generator.
        total_plies = sum(1 for _ in game.mainline_moves())

        return {
            "white": white,
            "black": black,
            "date": date,
            "total_plies": total_plies,
        }
