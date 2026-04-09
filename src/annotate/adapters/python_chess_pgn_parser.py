import io

import chess.pgn

from annotate.ports import PGNParser


class PythonChessPGNParser(PGNParser):
    def parse(self, pgn_text: str) -> dict:
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
