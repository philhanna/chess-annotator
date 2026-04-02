# chess_annotate.ports.pgn_parser
from __future__ import annotations

from abc import ABC, abstractmethod


class PGNParser(ABC):

    @abstractmethod
    def parse(self, pgn_text: str) -> dict:
        """Parse PGN text and return a dict with keys:
            white, black, date, total_plies
        """
        ...
