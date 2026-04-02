from abc import ABC, abstractmethod


class PGNParser(ABC):
    """Describe a service that parses PGN text into application metadata.

    The current application only needs lightweight information about a
    game at import time, so implementations return a compact dictionary
    rather than a fully wrapped domain object. Concrete adapters are
    responsible for validating the PGN and normalizing any metadata they
    expose to callers.
    """

    @abstractmethod
    def parse(self, pgn_text: str) -> dict:
        """Parse PGN text and return a dict with keys:
            white, black, date, total_plies
        """
        ...
