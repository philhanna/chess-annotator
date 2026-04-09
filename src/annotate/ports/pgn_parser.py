from abc import ABC, abstractmethod


class PGNParser(ABC):
    """Port for parsing PGN text into the lightweight metadata needed at import time.

    The application only needs a small set of game attributes when a PGN is first
    imported (player names, date, and total ply count), so implementations return a
    plain dict rather than a fully-modelled game object. Adapters are responsible
    for validating the PGN and normalising any metadata they expose.
    """

    @abstractmethod
    def parse(self, pgn_text: str) -> dict:
        """Parse ``pgn_text`` and return a metadata dict.

        Returns:
            A dict with the following keys:

            * ``"white"`` — name of the White player (str).
            * ``"black"`` — name of the Black player (str).
            * ``"date"``  — PGN Date header value, e.g. ``"2024.01.15"`` or
              ``"???"`` when absent (str).
            * ``"total_plies"`` — number of half-moves in the main line (int).

        Raises:
            ValueError: if the PGN text cannot be parsed.
        """
        ...
