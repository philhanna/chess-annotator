# annotate.cli
import io

import chess.pgn


def strip_comments(input_pgn: str) -> str:
    """Strip comments from PGN text using the python-chess library."""
    game = chess.pgn.read_game(io.StringIO(input_pgn))
    if game is None:
        raise ValueError("Could not parse PGN")
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=False)
    return game.accept(exporter)
