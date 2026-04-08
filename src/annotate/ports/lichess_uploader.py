from abc import ABC, abstractmethod


class LichessUploader(ABC):
    """Upload a PGN game to Lichess and return the resulting analysis URL.

    Implementations are responsible for the HTTP transport and URL
    extraction; the returned string should be a fully qualified Lichess
    game or analysis URL that the caller can open in a browser.
    """

    @abstractmethod
    def upload(self, pgn_text: str) -> str:
        """Upload ``pgn_text`` to Lichess and return the analysis URL."""
        ...
