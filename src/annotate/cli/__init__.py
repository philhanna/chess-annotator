# annotate.cli
import io

import chess.pgn


def strip_comments(input_pgn: str) -> str:
    """Return ``input_pgn`` with all comments removed from the main line.

    Uses python-chess to parse and re-export the game with the ``comments=False``
    flag. Raises ``ValueError`` if the PGN string cannot be parsed.
    """
    game = chess.pgn.read_game(io.StringIO(input_pgn))
    if game is None:
        raise ValueError("Could not parse PGN")
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=False)
    return game.accept(exporter)
